"""Groq chat completions, rate-limit headers, and per-model usage.

Header names follow Groq's rate-limit page (fetched 2026-11-16):
``x-ratelimit-limit-requests`` and ``x-ratelimit-remaining-requests`` are
requests per day, and the matching token headers are tokens per minute.
``retry-after`` is seconds and is only set on HTTP 429. Reset headers are
durations such as ``7.66s`` or ``2m59.56s``.
"""

import json
import re
import threading
import time
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace

from legacylift.providers.config import RoutingRules
from legacylift.providers.http import (
    USER_AGENT,
    HttpFailure,
    Transport,
    loads_object,
    urlopen_transport,
)
from legacylift.providers.types import (
    GroqSnapshot,
    ProviderCallError,
    TokenUsage,
    TranslationRequest,
    TranslationResponse,
)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

_LIMIT_HEADERS = (
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-tokens",
    "x-ratelimit-limit-requests",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-reset-requests",
)
_DURATION = re.compile(
    r"^(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+(?:\.\d+)?)s)?$"
)


def header_value(headers: Mapping[str, str], name: str) -> str | None:
    """Return one header, matching the name without case sensitivity.

    Args:
        headers: Response headers. Names may be any case.
        name: Header name to find.

    Returns:
        The stripped value, or ``None`` when the header is missing or blank.
    """
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted and value.strip():
            return value.strip()
    return None


def parse_duration(value: str | None) -> float | None:
    """Parse a Groq reset delay into seconds.

    Args:
        value: A duration such as ``7.66s`` or ``2m59.56s``, or ``None``.

    Returns:
        Seconds, or ``None`` when the value is missing or not that shape.
    """
    if not value:
        return None
    match = _DURATION.fullmatch(value.strip())
    if match is None or not any(match.groups()):
        return None
    hours = float(match.group("hours") or 0)
    minutes = float(match.group("minutes") or 0)
    seconds = float(match.group("seconds") or 0)
    return (hours * 3600) + (minutes * 60) + seconds


def parse_retry_after(headers: Mapping[str, str]) -> float | None:
    """Read ``retry-after`` as a number of seconds.

    Args:
        headers: Response headers.

    Returns:
        Seconds, or ``None`` when the header is missing or is an HTTP date.
    """
    raw = header_value(headers, "retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _optional_int(raw: str | None) -> int | None:
    """Parse an integer header. Blank or non-numeric values become ``None``."""
    if raw is None:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


@dataclass(frozen=True)
class ParsedGroqLimits:
    """Limit numbers found in one Groq response.

    Attributes:
        limit_tokens: TPM limit, if the header was present.
        remaining_tokens: TPM remaining, if present.
        reset_tokens: TPM reset text, if present.
        limit_requests: RPD limit, if present.
        remaining_requests: RPD remaining, if present.
        reset_requests: RPD reset text, if present.
        any_present: True when at least one recognized limit header was present.
    """

    limit_tokens: int | None = None
    remaining_tokens: int | None = None
    reset_tokens: str | None = None
    limit_requests: int | None = None
    remaining_requests: int | None = None
    reset_requests: str | None = None
    any_present: bool = False


def parse_groq_headers(headers: Mapping[str, str]) -> ParsedGroqLimits:
    """Read Groq's rate-limit headers. Missing headers stay ``None``.

    Args:
        headers: Response headers. Unknown names are ignored.

    Returns:
        The parsed limits. ``any_present`` is false when none of the six
        limit headers were included.
    """
    present = any(header_value(headers, name) is not None for name in _LIMIT_HEADERS)
    return ParsedGroqLimits(
        limit_tokens=_optional_int(header_value(headers, "x-ratelimit-limit-tokens")),
        remaining_tokens=_optional_int(header_value(headers, "x-ratelimit-remaining-tokens")),
        reset_tokens=header_value(headers, "x-ratelimit-reset-tokens"),
        limit_requests=_optional_int(header_value(headers, "x-ratelimit-limit-requests")),
        remaining_requests=_optional_int(header_value(headers, "x-ratelimit-remaining-requests")),
        reset_requests=header_value(headers, "x-ratelimit-reset-requests"),
        any_present=present,
    )


def _keep[T](new: T | None, previous: T | None) -> T | None:
    """Keep the previous value when the new response omitted a header."""
    return previous if new is None else new


def _low_budget_snapshot(snapshot: GroqSnapshot, fraction: float) -> bool:
    """Return whether remaining TPM or RPD is under ``fraction`` of its limit."""
    tokens_low = (
        snapshot.limit_tokens
        and snapshot.remaining_tokens is not None
        and snapshot.remaining_tokens / snapshot.limit_tokens < fraction
    )
    requests_low = (
        snapshot.limit_requests
        and snapshot.remaining_requests is not None
        and snapshot.remaining_requests / snapshot.limit_requests < fraction
    )
    return bool(tokens_low or requests_low)


class GroqUsageTracker:
    """In-memory Groq limits, one record per model.

    The record is updated from response headers. A session counter is kept
    even when those headers are missing.
    """

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self._models: dict[str, GroqSnapshot] = {}
        self._lock = threading.Lock()

    def snapshot(self, model: str, rules: RoutingRules, now: float) -> GroqSnapshot:
        """Return a copy of the model's state.

        Args:
            model: Groq model id.
            rules: Used for the low-budget warning text.
            now: Current epoch seconds, used only to phrase the warning.

        Returns:
            A snapshot. Before any response, ``has_header_data`` is false and
            the session counters are zero.
        """
        with self._lock:
            current = self._models.get(model) or GroqSnapshot(model=model)
            return self._with_warning(current, rules, now)

    def observe(
        self,
        model: str,
        headers: Mapping[str, str],
        *,
        tokens: int,
        rules: RoutingRules,
        now: float,
    ) -> GroqSnapshot:
        """Record a successful call.

        Args:
            model: Groq model id.
            headers: Response headers. Missing limit headers are left unset.
            tokens: Tokens to add to the session counter.
            rules: Supplies the low-budget fraction.
            now: Current epoch seconds.

        Returns:
            The updated snapshot.
        """
        return self._update(
            model, headers, tokens=tokens, requests=1, limited=False, rules=rules, now=now
        )

    def observe_limited(
        self,
        model: str,
        headers: Mapping[str, str],
        *,
        rules: RoutingRules,
        now: float,
    ) -> GroqSnapshot:
        """Record HTTP 429 and mark the model limited until the reset hint.

        Args:
            model: Groq model id.
            headers: Response headers, including ``retry-after`` when Groq sent it.
            rules: Supplies the low-budget fraction.
            now: Current epoch seconds.

        Returns:
            The updated snapshot. The request is counted. Tokens are not, because
            a rejected call does not report usage.
        """
        return self._update(
            model, headers, tokens=0, requests=1, limited=True, rules=rules, now=now
        )

    def _update(
        self,
        model: str,
        headers: Mapping[str, str],
        *,
        tokens: int,
        requests: int,
        limited: bool,
        rules: RoutingRules,
        now: float,
    ) -> GroqSnapshot:
        """Merge headers into the model record and return a copy."""
        parsed = parse_groq_headers(headers)
        with self._lock:
            current = self._models.get(model) or GroqSnapshot(model=model)
            updated = replace(
                current,
                limit_tokens=_keep(parsed.limit_tokens, current.limit_tokens),
                remaining_tokens=_keep(parsed.remaining_tokens, current.remaining_tokens),
                reset_tokens=_keep(parsed.reset_tokens, current.reset_tokens),
                limit_requests=_keep(parsed.limit_requests, current.limit_requests),
                remaining_requests=_keep(parsed.remaining_requests, current.remaining_requests),
                reset_requests=_keep(parsed.reset_requests, current.reset_requests),
                session_requests=current.session_requests + requests,
                session_tokens=current.session_tokens + max(tokens, 0),
                has_header_data=current.has_header_data or parsed.any_present,
                low_budget=current.low_budget,
                rate_limited_until=None,
            )
            updated = replace(
                updated, low_budget=_low_budget_snapshot(updated, rules.low_budget_fraction)
            )
            if limited:
                delay = parse_retry_after(headers)
                if delay is None:
                    delay = parse_duration(parsed.reset_tokens) or parse_duration(
                        parsed.reset_requests
                    )
                if delay is None:
                    delay = 60.0
                updated = replace(updated, rate_limited_until=now + max(delay, 0))
            self._models[model] = updated
            return self._with_warning(updated, rules, now)

    def _with_warning(
        self, snapshot: GroqSnapshot, rules: RoutingRules, now: float
    ) -> GroqSnapshot:
        """Attach the warning string for a low or rate-limited budget."""
        percent = int(rules.low_budget_fraction * 100)
        if snapshot.rate_limited_until is not None and snapshot.rate_limited_until > now:
            wait = max(snapshot.rate_limited_until - now, 0)
            return replace(snapshot, warning=f"Groq is rate-limited. Try again in {wait:.0f}s.")
        if snapshot.low_budget:
            return replace(snapshot, warning=f"Groq budget is below {percent}% of the limit.")
        return replace(snapshot, warning="")

    def models(self) -> list[str]:
        """Return the model ids that have any recorded state."""
        with self._lock:
            return list(self._models)


def retry_delay(headers: Mapping[str, str]) -> float | None:
    """Choose how long a single 429 retry should wait.

    Args:
        headers: Response headers from the 429.

    Returns:
        Seconds from ``retry-after``, otherwise from a reset duration, or
        ``None`` when Groq gave no numeric hint.
    """
    delay = parse_retry_after(headers)
    if delay is not None:
        return delay
    parsed = parse_groq_headers(headers)
    return parse_duration(parsed.reset_tokens) or parse_duration(parsed.reset_requests)


class GroqProvider:
    """Send one chat completion to Groq and update :class:`GroqUsageTracker`.

    Attributes:
        name: Always ``groq``.
        api_key: ``LEGACYLIFT_GROQ_API_KEY``, or ``None`` when unset.
        tracker: Shared per-model usage.
    """

    name = "groq"

    def __init__(
        self,
        api_key: str | None,
        *,
        timeout: float,
        rules: RoutingRules,
        tracker: GroqUsageTracker | None = None,
        transport: Transport = urlopen_transport,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Store the key and the hooks tests replace.

        Args:
            api_key: Groq key. ``None`` or blank means Groq is not configured.
            timeout: Seconds for one HTTP call.
            rules: Routing numbers, including the short 429 retry cap.
            tracker: Shared usage. A new tracker is created when omitted.
            transport: HTTP caller. Tests pass a fake.
            clock: Epoch-second clock.
            sleep: Used for one short 429 retry. Tests pass a recorder.
        """
        self.api_key = api_key.strip() if api_key and api_key.strip() else None
        self.timeout = timeout
        self.rules = rules
        self.tracker = tracker or GroqUsageTracker()
        self.transport = transport
        self.clock = clock
        self.sleep = sleep

    def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Send ``request`` to Groq.

        A 429 is retried once when the hint is within ``groq_retry_max_seconds``.
        A longer hint marks the model limited and raises, so the router can fall
        back instead of sleeping.

        Args:
            request: Prompt, purpose, and the Groq model id.

        Returns:
            The completion text, usage, and the updated rate-limit snapshot.

        Raises:
            ProviderCallError: Groq is unset, rate-limited, timed out, or
                returned a body that was not a chat completion.
        """
        if self.api_key is None:
            raise ProviderCallError("groq", "Groq is not configured.", kind="unconfigured")
        now = self.clock()
        state = self.tracker.snapshot(request.groq_model, self.rules, now)
        if state.rate_limited_until is not None and state.rate_limited_until > now:
            raise ProviderCallError(
                "groq", state.warning or "Groq is rate-limited.", kind="rate_limit"
            )
        return self._send(request, allow_retry=True, json_mode=True)

    def _send(
        self, request: TranslationRequest, *, allow_retry: bool, json_mode: bool
    ) -> TranslationResponse:
        """Perform one Groq call, optionally retrying a short 429 a single time."""
        http_request = urllib.request.Request(
            GROQ_CHAT_URL,
            data=json.dumps(_chat_body(request, json_mode=json_mode)).encode(),
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
            return self._failed(request, error, allow_retry=allow_retry, json_mode=json_mode)
        try:
            payload = loads_object(result.body)
        except json.JSONDecodeError as error:
            raise ProviderCallError(
                "groq", "Groq returned a body that was not JSON.", kind="malformed"
            ) from error
        text = _message_text(payload)
        usage = _usage(payload)
        tokens = (
            usage.total_tokens
            if usage and usage.total_tokens is not None
            else request.estimated_tokens
        )
        snapshot = self.tracker.observe(
            request.groq_model,
            result.headers,
            tokens=tokens,
            rules=self.rules,
            now=self.clock(),
        )
        return TranslationResponse(
            text=text,
            provider="groq",
            model=request.groq_model,
            usage=usage,
            rate_limit_state=snapshot,
        )

    def _failed(
        self,
        request: TranslationRequest,
        error: HttpFailure,
        *,
        allow_retry: bool,
        json_mode: bool,
    ) -> TranslationResponse:
        """Record a 429, maybe retry once, and otherwise raise ``ProviderCallError``."""
        if allow_retry and json_mode and "json_validate_failed" in error.body:
            return self._send(request, allow_retry=False, json_mode=False)
        if error.kind == "rate_limit":
            self.tracker.observe_limited(
                request.groq_model, error.headers, rules=self.rules, now=self.clock()
            )
            delay = retry_delay(error.headers)
            if allow_retry and delay is not None and delay <= self.rules.groq_retry_max_seconds:
                self.sleep(max(delay, 0))
                return self._send(request, allow_retry=False, json_mode=json_mode)
            raise ProviderCallError(
                "groq",
                "Groq rate limit reached.",
                kind="rate_limit",
                headers=error.headers,
            ) from error
        raise ProviderCallError(
            "groq", str(error), kind=error.kind, headers=error.headers
        ) from error


def _chat_body(request: TranslationRequest, *, json_mode: bool = True) -> dict[str, object]:
    """Build an OpenAI-style chat body. The key is not part of the body."""
    prompt = request.prompt
    body: dict[str, object] = {
        "model": request.groq_model,
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
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if "gpt-oss" in request.groq_model:
            # This model spends the token budget on reasoning unless it is kept low.
            body["reasoning_effort"] = "low"
            body["max_completion_tokens"] = 4096
        else:
            body["max_tokens"] = 2048
    return body


def _message_text(payload: object) -> str:
    """Return the first choice's message content."""
    if not isinstance(payload, dict):
        raise ProviderCallError(
            "groq", "Groq returned a body that was not a chat completion.", kind="malformed"
        )
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ProviderCallError(
            "groq", "Groq returned a body that was not a chat completion.", kind="malformed"
        )
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ProviderCallError(
            "groq", "Groq returned a body that was not a chat completion.", kind="malformed"
        )
    content = _completion_text(message)
    if content is None:
        raise ProviderCallError("groq", "Groq returned an empty completion.", kind="malformed")
    return content


def _completion_text(message: dict[str, object]) -> str | None:
    """Return message text. Some Groq models put it in ``reasoning``."""
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    reasoning = message.get("reasoning")
    if isinstance(reasoning, str) and '"matches"' in reasoning:
        return reasoning
    return None


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
