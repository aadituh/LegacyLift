"""OpenRouter chat completions, the model catalog, and the local request cap.

OpenRouter limits are not shown as a progress bar. This module counts requests
in a sliding window and refuses to send once the configured cap is reached.
"""

import hashlib
import json
import threading
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from legacylift.cobol.ai_review import _parse_findings
from legacylift.errors import AIReviewError
from legacylift.providers.config import RoutingRules
from legacylift.providers.groq import GROQ_MODELS_URL
from legacylift.providers.http import (
    USER_AGENT,
    HttpFailure,
    Transport,
    loads_object,
    urlopen_transport,
)
from legacylift.providers.types import (
    ModelInfo,
    ProviderCallError,
    TokenUsage,
    TranslationRequest,
    TranslationResponse,
)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_NON_TEXT_MARKERS = ("whisper", "tts", "orpheus", "embed")


def format_wait(seconds: float) -> str:
    """Format a short wait for a limit message.

    Args:
        seconds: Seconds until the oldest counted request leaves the window.

    Returns:
        A phrase such as ``45 seconds`` or ``3 hours 2 minutes``.
    """
    remaining = max(int(seconds + 0.999), 0)
    if remaining < 60:
        unit = "second" if remaining == 1 else "seconds"
        return f"{remaining} {unit}"
    minutes, secs = divmod(remaining, 60)
    hours, minutes = divmod(minutes, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour" if hours == 1 else f"{hours} hours")
    if minutes:
        parts.append(f"{minutes} minute" if minutes == 1 else f"{minutes} minutes")
    if not parts:
        parts.append(f"{secs} seconds")
    return " ".join(parts)


class SlidingWindowLimiter:
    """Count OpenRouter calls and block the next one that would pass a cap.

    The window is local to this process. It is the client of OpenRouter: the
    check happens before the request is sent.
    """

    def __init__(self, *, per_minute: int, per_day: int) -> None:
        """Store the caps.

        Args:
            per_minute: Maximum calls in any 60-second window.
            per_day: Maximum calls in any 24-hour window.
        """
        self.per_minute = per_minute
        self.per_day = per_day
        self._hits: list[float] = []
        self._lock = threading.Lock()

    def status(self, now: float) -> str | None:
        """Return a limit message, or ``None`` when another call is allowed.

        Args:
            now: Current epoch seconds.

        Returns:
            A message naming the cap and the wait, or ``None``.
        """
        with self._lock:
            return self._status(now)

    def acquire(self, now: float) -> str | None:
        """Consume one slot, or return the limit message without consuming it.

        Args:
            now: Current epoch seconds.

        Returns:
            ``None`` when the call was recorded. Otherwise the same message as
            :meth:`status`, and the call is not recorded.
        """
        with self._lock:
            message = self._status(now)
            if message is not None:
                return message
            self._hits.append(now)
            return None

    def _status(self, now: float) -> str | None:
        """Return the block message. The caller holds ``_lock``."""
        day_window = 86_400
        self._hits = [hit for hit in self._hits if now - hit < day_window]
        if len(self._hits) >= self.per_day:
            wait = self._hits[0] + day_window - now
            return (
                f"OpenRouter limit reached: maximum of {self.per_day} requests per day. "
                f"Try again in {format_wait(wait)}."
            )
        minute_hits = [hit for hit in self._hits if now - hit < 60]
        if len(minute_hits) >= self.per_minute:
            wait = minute_hits[0] + 60 - now
            return (
                f"OpenRouter limit reached: maximum of {self.per_minute} requests per minute. "
                f"Try again in {format_wait(wait)}."
            )
        return None


def _digest(api_key: str | None) -> str:
    """Return a short hash so the cache can tell keys apart without storing one."""
    if not api_key:
        return ""
    return hashlib.sha256(api_key.encode()).hexdigest()[:12]


@dataclass
class _CacheEntry:
    """One cached model list."""

    stored_at: float
    digest: str
    models: list[ModelInfo]


class ModelCatalog:
    """Fetch Groq and OpenRouter model lists and reuse them until the TTL."""

    def __init__(
        self,
        rules: RoutingRules,
        *,
        transport: Transport = urlopen_transport,
    ) -> None:
        """Store the TTL and the HTTP caller.

        Args:
            rules: Supplies the TTL and the catalog timeout.
            transport: HTTP caller. Tests pass a fake.
        """
        self.rules = rules
        self.transport = transport
        self._groq: _CacheEntry | None = None
        self._openrouter: _CacheEntry | None = None
        self._lock = threading.Lock()

    def groq_models(self, api_key: str | None, now: float) -> tuple[list[ModelInfo], str]:
        """Return Groq models for this key, using the cache when it is fresh.

        Args:
            api_key: Groq key. ``None`` skips the request and returns no models.
            now: Current epoch seconds.

        Returns:
            The models, and an empty string or a short error that omits the key.
        """
        if not api_key:
            return [], ""
        return self._cached(
            "groq",
            api_key,
            now,
            urllib.request.Request(
                GROQ_MODELS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                method="GET",
            ),
        )

    def openrouter_models(self, api_key: str | None, now: float) -> tuple[list[ModelInfo], str]:
        """Return OpenRouter models, using the cache when it is fresh.

        Args:
            api_key: OpenRouter key, sent when it is set. The public list is
                requested when it is missing.
            now: Current epoch seconds.

        Returns:
            The models, and an empty string or a short error that omits the key.
        """
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        return self._cached(
            "openrouter",
            api_key,
            now,
            urllib.request.Request(OPENROUTER_MODELS_URL, headers=headers, method="GET"),
        )

    def _cached(
        self,
        provider: str,
        api_key: str | None,
        now: float,
        request: urllib.request.Request,
    ) -> tuple[list[ModelInfo], str]:
        """Return the cached list or fetch it. Errors keep a fresh-enough stale list."""
        digest = _digest(api_key)
        with self._lock:
            current = self._groq if provider == "groq" else self._openrouter
            if (
                current is not None
                and current.digest == digest
                and now - current.stored_at < self.rules.model_catalog_ttl_seconds
            ):
                return list(current.models), ""
        try:
            result = self.transport(request, self.rules.catalog_timeout_seconds)
            models = _parse_models(loads_object(result.body), free_only=provider == "openrouter")
        except (HttpFailure, json.JSONDecodeError):
            with self._lock:
                stale = self._groq if provider == "groq" else self._openrouter
                if stale is not None and stale.digest == digest:
                    return list(stale.models), f"{_label(provider)} model list could not be refreshed."
            return [], f"{_label(provider)} model list could not be loaded."
        entry = _CacheEntry(stored_at=now, digest=digest, models=models)
        with self._lock:
            if provider == "groq":
                self._groq = entry
            else:
                self._openrouter = entry
        return list(models), ""


def _label(provider: str) -> str:
    """Return the display name for a catalog error."""
    if provider == "groq":
        return "Groq"
    return "OpenRouter"


def _parse_models(payload: object, *, free_only: bool = False) -> list[ModelInfo]:
    """Read ``{"data": [{"id", "name"}]}`` and drop non-text model ids.

    Args:
        payload: JSON from a models endpoint.
        free_only: Keep names that end with ``(free)``. OpenRouter uses that
            suffix for its free models.
    """
    if not isinstance(payload, dict):
        raise json.JSONDecodeError("model list was not an object", "", 0)
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise json.JSONDecodeError("model list had no data", "", 0)
    models: list[ModelInfo] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = row.get("id")
        if not isinstance(model_id, str) or not model_id.strip():
            continue
        if any(marker in model_id.lower() for marker in _NON_TEXT_MARKERS):
            continue
        name = row.get("name")
        label = name.strip() if isinstance(name, str) and name.strip() else model_id
        if free_only and not label.lower().endswith("(free)"):
            continue
        models.append(ModelInfo(id=model_id, name=label))
    models.sort(key=lambda item: item.name.lower())
    return models


class OpenRouterProvider:
    """Send one chat completion to OpenRouter if the local cap allows it.

    Attributes:
        name: Always ``openrouter``.
        api_key: ``LEGACYLIFT_OPENROUTER_API_KEY``, or ``None`` when unset.
        limiter: Sliding-window counter.
    """

    name = "openrouter"

    def __init__(
        self,
        api_key: str | None,
        *,
        timeout: float,
        rules: RoutingRules,
        limiter: SlidingWindowLimiter | None = None,
        transport: Transport = urlopen_transport,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Store the key and the limiter.

        Args:
            api_key: OpenRouter key. ``None`` or blank means it is not configured.
            timeout: Seconds for one HTTP call.
            rules: Supplies the daily and per-minute caps.
            limiter: Shared counter. A new one is created when omitted.
            transport: HTTP caller. Tests pass a fake.
            clock: Epoch-second clock.
        """
        self.api_key = api_key.strip() if api_key and api_key.strip() else None
        self.timeout = timeout
        self.rules = rules
        self.limiter = limiter or SlidingWindowLimiter(
            per_minute=rules.openrouter_requests_per_minute,
            per_day=rules.openrouter_requests_per_day,
        )
        self.transport = transport
        self.clock = clock

    def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Send ``request`` unless the local cap is already reached.

        Args:
            request: Prompt, purpose, and the OpenRouter model id.

        Returns:
            The completion text and usage. ``rate_limit_state`` stays ``None``.

        Raises:
            ProviderCallError: The key is unset, the local cap blocked the call,
                or OpenRouter timed out or returned a body that was not a completion.
        """
        if self.api_key is None:
            raise ProviderCallError("openrouter", "OpenRouter is not configured.", kind="unconfigured")
        blocked = self.limiter.acquire(self.clock())
        if blocked is not None:
            raise ProviderCallError("openrouter", blocked, kind="limited")
        return self._send(request, reasoning=True)

    def _send(
        self, request: TranslationRequest, *, reasoning: bool, recover: bool = True
    ) -> TranslationResponse:
        """Send one chat completion. Retry once if a model rejects the reasoning cap."""
        http_request = urllib.request.Request(
            OPENROUTER_CHAT_URL,
            data=json.dumps(_chat_body(request, reasoning=reasoning)).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            result = self.transport(http_request, self.timeout)
        except HttpFailure as error:
            if reasoning and error.status == 400 and "reasoning" in error.body.lower():
                return self._send(request, reasoning=False, recover=recover)
            raise ProviderCallError(
                "openrouter",
                _account_restriction(error.body) or str(error),
                kind=error.kind,
                headers=error.headers,
            ) from error
        try:
            payload = loads_object(result.body)
        except json.JSONDecodeError as error:
            raise ProviderCallError(
                "openrouter", "OpenRouter returned a body that was not JSON.", kind="malformed"
            ) from error
        try:
            text = _message_text(payload)
        except ProviderCallError as error:
            trace = _reasoning_text(payload)
            if recover and request.purpose == "review" and trace and error.kind == "malformed":
                return self._review_from_reasoning(request, trace)
            raise
        if recover and request.purpose == "review" and not _is_findings(text):
            trace = _reasoning_text(payload) or text
            if trace.strip():
                return self._review_from_reasoning(request, trace)
        return TranslationResponse(
            text=text,
            provider="openrouter",
            model=request.openrouter_model,
            usage=_usage(payload),
        )

    def _review_from_reasoning(self, request: TranslationRequest, reasoning: str) -> TranslationResponse:
        """Ask the same model to turn a reasoning trace into the review JSON.

        A short prompt is used because the long review makes some free models
        spend the whole reply on reasoning.

        Raises:
            ProviderCallError: The cap is already spent, or the follow-up has no JSON.
        """
        blocked = self.limiter.acquire(self.clock())
        if blocked is not None:
            raise ProviderCallError("openrouter", blocked, kind="limited")
        excerpt = reasoning.strip()
        if len(excerpt) > 1200:
            excerpt = excerpt[-1200:]
        prompt = (
            'Output only this JSON and nothing else, using integer line numbers: '
            '{"matches":[{"cobol_lines":[1],"python_lines":[1],"detail":"text"}],'
            '"concerns":[]}\n\nAnalysis:\n'
            f"{excerpt}"
        )
        http_request = urllib.request.Request(
            OPENROUTER_CHAT_URL,
            data=json.dumps(
                {
                    "model": request.openrouter_model,
                    "temperature": 0,
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            result = self.transport(http_request, self.timeout)
        except HttpFailure as error:
            raise ProviderCallError(
                "openrouter",
                _account_restriction(error.body) or str(error),
                kind=error.kind,
                headers=error.headers,
            ) from error
        try:
            payload = loads_object(result.body)
        except json.JSONDecodeError as error:
            raise ProviderCallError(
                "openrouter", "OpenRouter returned a body that was not JSON.", kind="malformed"
            ) from error
        return TranslationResponse(
            text=_message_text(payload),
            provider="openrouter",
            model=request.openrouter_model,
            usage=_usage(payload),
        )


def _chat_body(request: TranslationRequest, *, reasoning: bool = True) -> dict[str, object]:
    """Build an OpenAI-style chat body. The key is not part of the body."""
    prompt = request.prompt
    body: dict[str, object] = {
        "model": request.openrouter_model,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }
    if request.purpose == "review":
        prompt = (
            f"{request.prompt}\n\n"
            'Respond with JSON: {"matches":[{"cobol_lines":[],"python_lines":[],"detail":""}],'
            '"concerns":[]}'
        )
        body["messages"] = [{"role": "user", "content": prompt}]
        body["response_format"] = {"type": "json_object"}
        # Leave room for the JSON answer. ERNIE otherwise uses the whole budget on reasoning.
        body["max_tokens"] = 4096
        if reasoning:
            body["reasoning"] = {"max_tokens": 512}
    return body


def _message_text(payload: object) -> str:
    """Return the first choice's message content."""
    if not isinstance(payload, dict):
        raise ProviderCallError(
            "openrouter", "OpenRouter returned a body that was not a chat completion.", kind="malformed"
        )
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ProviderCallError(
            "openrouter", "OpenRouter returned a body that was not a chat completion.", kind="malformed"
        )
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ProviderCallError(
            "openrouter", "OpenRouter returned a body that was not a chat completion.", kind="malformed"
        )
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    reasoning = message.get("reasoning")
    if isinstance(reasoning, str) and '"matches"' in reasoning:
        return reasoning
    if isinstance(reasoning, str) and reasoning.strip():
        raise ProviderCallError(
            "openrouter",
            "The model returned reasoning but not the review JSON.",
            kind="malformed",
        )
    raise ProviderCallError("openrouter", "OpenRouter returned an empty completion.", kind="malformed")


def _account_restriction(body: str) -> str:
    """Explain an OpenRouter account block, or return an empty string."""
    if "free-model-training-violation" in body or "Free model training violation" in body:
        return (
            "OpenRouter blocked this free model because the workspace guardrail "
            "disallows models that train on prompts. Allow them at "
            "https://openrouter.ai/workspaces/default/guardrails"
        )
    if "agentic harnesses" in body:
        return (
            "OpenRouter only serves this model through an agent app, not this API. "
            "See https://openrouter.ai/apps"
        )
    return ""


def _is_findings(text: str) -> bool:
    """Return whether ``text`` is a review the rest of the pipeline can read."""
    try:
        _parse_findings(text)
    except AIReviewError:
        return False
    return True


def _reasoning_text(payload: object) -> str:
    """Return the reasoning trace, or an empty string when the body has none."""
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""
    reasoning = message.get("reasoning")
    if isinstance(reasoning, str):
        return reasoning
    return ""


def _usage(payload: object) -> TokenUsage | None:
    """Read an OpenAI-style ``usage`` object, or ``None`` when it is absent."""
    if not isinstance(payload, dict):
        return None
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None

    def number(name: str) -> int | None:
        raw = usage.get(name)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None
        return int(raw)

    return TokenUsage(
        prompt_tokens=number("prompt_tokens"),
        completion_tokens=number("completion_tokens"),
        total_tokens=number("total_tokens"),
    )
