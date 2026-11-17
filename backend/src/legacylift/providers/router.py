"""Choose a translation provider and fall back once along that order.

Auto mode routes large estimates to Gemini, small estimates to Groq when Groq
has budget, and otherwise to OpenRouter or Gemini. A manual choice starts at
that provider. Each timeout, 5xx, or malformed response tries the next provider
once. The same provider is not retried in a loop; Groq's own short 429 retry
stays inside ``GroqProvider``.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable

from legacylift.cobol.ai_review import _parse_findings
from legacylift.config import Settings
from legacylift.errors import (
    AIReviewError,
    InvalidInputError,
    ProjectStateError,
    ProviderLimitError,
)
from legacylift.providers.config import (
    GROQ_MODEL_CHOICES,
    OPENROUTER_MODEL_CHOICES,
    ROUTING_RULES,
    RoutingRules,
)
from legacylift.providers.estimate import estimate_total, format_tokens
from legacylift.providers.gemini import GeminiProvider
from legacylift.providers.groq import GroqProvider, GroqUsageTracker
from legacylift.providers.openrouter import ModelCatalog, OpenRouterProvider
from legacylift.providers.types import (
    GroqSnapshot,
    ModelChoice,
    ModelInfo,
    ProviderCallError,
    RoutePlan,
    TranslationRequest,
    TranslationResponse,
)

logger = logging.getLogger(__name__)

DISPLAY = {"groq": "Groq", "openrouter": "OpenRouter", "gemini": "Gemini"}
GeminiCall = Callable[[TranslationRequest], TranslationResponse]
_MODES = {"auto", "gemini", "groq", "openrouter"}
_MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,199}$")


def parse_model_choice(
    mode: str,
    groq_model: str | None = None,
    openrouter_model: str | None = None,
) -> ModelChoice:
    """Validate the query parameters from the review and describe routes.

    Args:
        mode: ``auto``, ``gemini``, ``groq``, or ``openrouter``.
        groq_model: Optional Groq model id.
        openrouter_model: Optional OpenRouter model id.

    Returns:
        The choice the router should use.

    Raises:
        InvalidInputError: The mode or a model id is not usable.
    """
    if mode not in _MODES:
        raise InvalidInputError("Model mode must be auto, gemini, groq, or openrouter.")
    return ModelChoice(
        mode=mode,
        groq_model=_clean_model_id(groq_model),
        openrouter_model=_clean_model_id(openrouter_model),
    )


def _clean_model_id(model: str | None) -> str | None:
    """Return a stripped model id, or ``None`` when the query omitted it."""
    if model is None or not model.strip():
        return None
    cleaned = model.strip()
    if _MODEL_ID.fullmatch(cleaned) is None:
        raise InvalidInputError("Model id contains unsupported characters.")
    return cleaned


def groq_budget_block(
    state: GroqSnapshot | None,
    estimated: int,
    rules: RoutingRules,
    now: float,
) -> str | None:
    """Return why Groq should be skipped, or ``None`` when it can take the call.

    Missing header data does not block Groq. A rate-limit window, an empty RPD
    or TPM balance, or a remaining share under ``rules.low_budget_fraction`` does.

    Args:
        state: Latest snapshot, or ``None`` before any call.
        estimated: Input tokens plus reserved output tokens.
        rules: Routing numbers.
        now: Current epoch seconds.

    Returns:
        A short reason, or ``None`` when Groq is eligible.
    """
    if state is None:
        return None
    if state.rate_limited_until is not None and state.rate_limited_until > now:
        return "Groq is rate-limited"
    if not state.has_header_data:
        return None
    if state.remaining_requests is not None and state.remaining_requests < 1:
        return "Groq RPD is exhausted"
    if state.remaining_tokens is not None and estimated > state.remaining_tokens:
        return "estimated tokens exceed Groq's remaining TPM"
    low = False
    if state.limit_tokens and state.remaining_tokens is not None:
        low = state.remaining_tokens / state.limit_tokens < rules.low_budget_fraction
    if state.limit_requests and state.remaining_requests is not None:
        low = low or state.remaining_requests / state.limit_requests < rules.low_budget_fraction
    if low:
        percent = int(rules.low_budget_fraction * 100)
        return f"Groq remaining budget is below {percent}%"
    return None


def fallback_chain(
    start: str,
    *,
    groq_configured: bool,
    openrouter_configured: bool,
) -> tuple[str, ...]:
    """Return the providers to try, starting at ``start`` and moving toward Gemini.

    Args:
        start: ``groq``, ``openrouter``, or ``gemini``.
        groq_configured: Include Groq when it is not the selected start.
        openrouter_configured: Include OpenRouter when it is not the selected start.

    Returns:
        The ordered provider keys. The selected start is kept even when that
        provider is not configured, so the failure is visible before fallback.
    """
    order = ("groq", "openrouter", "gemini")
    chosen: list[str] = []
    for name in order[order.index(start) :]:
        if name == "groq" and not groq_configured and start != "groq":
            continue
        if name == "openrouter" and not openrouter_configured and start != "openrouter":
            continue
        chosen.append(name)
    return tuple(chosen) or ("gemini",)


def plan_route(
    *,
    estimated_tokens: int,
    choice: ModelChoice,
    rules: RoutingRules,
    groq_configured: bool,
    openrouter_configured: bool,
    groq_state: GroqSnapshot | None,
    openrouter_block: str | None,
    now: float,
) -> RoutePlan:
    """Choose the provider order for one request.

    Args:
        estimated_tokens: Input tokens plus reserved output tokens.
        choice: Manual provider, or auto.
        rules: Thresholds and default model ids.
        groq_configured: A Groq key is set.
        openrouter_configured: An OpenRouter key is set.
        groq_state: Usage for the Groq model this request would call.
        openrouter_block: Limiter message when OpenRouter would refuse the call.
        now: Current epoch seconds.

    Returns:
        The providers to try and the note to show. ``limit_message`` is set
        when an explicit OpenRouter choice must not be sent.
    """
    count = format_tokens(estimated_tokens)
    groq_model = choice.groq_model or rules.default_groq_model
    openrouter_model = choice.openrouter_model or rules.default_openrouter_model
    if choice.mode == "gemini":
        return RoutePlan(("gemini",), f"Routed to Gemini: selected {rules.gemini_model}.")
    if choice.mode == "groq":
        return RoutePlan(
            fallback_chain(
                "groq",
                groq_configured=groq_configured,
                openrouter_configured=openrouter_configured,
            ),
            f"Routed to Groq: selected {groq_model}.",
        )
    if choice.mode == "openrouter":
        if openrouter_configured and openrouter_block:
            return RoutePlan(("openrouter",), openrouter_block, limit_message=openrouter_block)
        return RoutePlan(
            fallback_chain(
                "openrouter",
                groq_configured=groq_configured,
                openrouter_configured=openrouter_configured,
            ),
            f"Routed to OpenRouter: selected {openrouter_model}.",
        )
    if estimated_tokens > rules.groq_per_request_token_limit:
        return RoutePlan(
            ("gemini",),
            f"Routed to Gemini: {count} tokens, above the Groq per-request limit.",
        )
    if estimated_tokens > rules.gemini_token_threshold:
        return RoutePlan(
            ("gemini",),
            f"Routed to Gemini: {count} tokens, above the routing threshold.",
        )
    blocked = groq_budget_block(groq_state, estimated_tokens, rules, now)
    if groq_configured and blocked is None:
        if groq_state is not None and groq_state.has_header_data:
            detail = "within remaining TPM"
        else:
            detail = "no rate-limit data yet"
        return RoutePlan(
            fallback_chain(
                "groq",
                groq_configured=True,
                openrouter_configured=openrouter_configured,
            ),
            f"Routed to Groq: {count} tokens, {detail}.",
        )
    why = blocked or "Groq is not configured"
    if openrouter_configured and not openrouter_block:
        return RoutePlan(
            fallback_chain(
                "openrouter",
                groq_configured=False,
                openrouter_configured=True,
            ),
            f"Routed to OpenRouter: {why}.",
        )
    if openrouter_block and openrouter_configured:
        why = f"{why}; {openrouter_block}"
    elif not openrouter_configured and blocked:
        why = f"{why} and OpenRouter is not configured"
    elif not openrouter_configured:
        why = "Groq is not configured and OpenRouter is not configured"
    return RoutePlan(("gemini",), f"Routed to Gemini: {why}.")


class Translator:
    """Route a translation and call the shared provider interface.

    Attributes:
        rules: Thresholds and caps.
        groq: Groq provider and its usage tracker.
        openrouter: OpenRouter provider and its limiter.
        catalog: Cached model lists.
    """

    def __init__(
        self,
        *,
        gemini: GeminiProvider,
        groq: GroqProvider,
        openrouter: OpenRouterProvider,
        catalog: ModelCatalog,
        rules: RoutingRules = ROUTING_RULES,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Store the providers. Construction does not call the network.

        Args:
            gemini: Gemini provider.
            groq: Groq provider.
            openrouter: OpenRouter provider.
            catalog: Model-list cache.
            rules: Routing numbers.
            clock: Epoch-second clock.
        """
        self.gemini = gemini
        self.groq = groq
        self.openrouter = openrouter
        self.catalog = catalog
        self.rules = rules
        self.clock = clock

    @classmethod
    def from_settings(cls, settings: Settings) -> Translator:
        """Build the providers from environment-backed settings.

        Args:
            settings: Application settings. Keys stay on the providers.

        Returns:
            A translator that shares one Groq tracker and one OpenRouter limiter.
        """
        rules = ROUTING_RULES
        timeout = settings.gemini_timeout_seconds
        tracker = GroqUsageTracker()
        return cls(
            gemini=GeminiProvider(settings.gemini_api_key, timeout=timeout, rules=rules),
            groq=GroqProvider(settings.groq_api_key, timeout=timeout, rules=rules, tracker=tracker),
            openrouter=OpenRouterProvider(settings.openrouter_api_key, timeout=timeout, rules=rules),
            catalog=ModelCatalog(rules),
            rules=rules,
        )

    def translate(
        self,
        request: TranslationRequest,
        choice: ModelChoice,
        *,
        gemini: GeminiCall | None = None,
    ) -> TranslationResponse:
        """Translate ``request``, falling back along the routing order.

        Args:
            request: Prompt and purpose. Token estimate and model ids are filled
                from ``choice`` and the rules when they are blank.
            choice: Auto, or a provider the user selected.
            gemini: Replacement for the Gemini provider. The project service
                passes the existing ``request_gemini_review`` / ``complete``
                functions so tests that replace those names still apply.

        Returns:
            The model text, the provider that produced it, and the routing note.

        Raises:
            ProviderLimitError: An explicit OpenRouter choice is over the local cap.
            AIReviewError: Every provider in the order failed. A Gemini-only
                failure is re-raised unchanged.
            ProjectStateError: The Gemini description client failed and it was
                the only provider tried.
        """
        estimated = request.estimated_tokens or estimate_total(request.prompt, self.rules)
        prepared = TranslationRequest(
            prompt=request.prompt,
            purpose=request.purpose,
            estimated_tokens=estimated,
            groq_model=choice.groq_model or self.rules.default_groq_model,
            openrouter_model=choice.openrouter_model or self.rules.default_openrouter_model,
        )
        now = self.clock()
        state = self.groq.tracker.snapshot(prepared.groq_model, self.rules, now)
        openrouter_block = self.openrouter.limiter.status(now) if self.openrouter.api_key else None
        plan = plan_route(
            estimated_tokens=estimated,
            choice=choice,
            rules=self.rules,
            groq_configured=self.groq.api_key is not None,
            openrouter_configured=self.openrouter.api_key is not None,
            groq_state=state,
            openrouter_block=openrouter_block,
            now=now,
        )
        if plan.limit_message:
            raise ProviderLimitError(plan.limit_message)
        failures: list[tuple[str, Exception]] = []
        notes = [plan.reason]
        for name in plan.providers:
            try:
                response = self._invoke(name, prepared, gemini)
                if prepared.purpose == "review":
                    response.text = _canonical_review(name, response.text)
                elif not response.text.strip():
                    raise ProviderCallError(
                        name, f"{DISPLAY[name]} returned an empty response.", kind="malformed"
                    )
            except ProviderLimitError:
                raise
            except ProviderCallError as error:
                if error.kind == "limited" and choice.mode == "openrouter":
                    raise ProviderLimitError(str(error)) from error
                # A chosen provider's 4xx is reported immediately. Falling through
                # the other providers turns a fast rejection into a client timeout.
                if choice.mode != "auto" and error.kind not in {"timeout", "server", "rate_limit"}:
                    raise AIReviewError(f"{DISPLAY[name]}: {error}") from error
                failures.append((name, error))
                notes.append(f"Fell back from {DISPLAY[name]}: {_public_error(error)}.")
                continue
            except (AIReviewError, ProjectStateError, TimeoutError, OSError) as error:
                failures.append((name, error))
                notes.append(f"Fell back from {DISPLAY[name]}: {_public_error(error)}.")
                continue
            if failures:
                notes.append(f"Fell back to {DISPLAY[name]}.")
            response.routing_note = " ".join(notes)
            response.rate_limit_state = self.groq.tracker.snapshot(
                prepared.groq_model, self.rules, self.clock()
            )
            logger.info("Translation routing: %s", response.routing_note)
            return response
        _raise_failures(failures)
        raise AIReviewError("Translation failed. Tried no providers.")

    def _invoke(
        self,
        name: str,
        request: TranslationRequest,
        gemini: GeminiCall | None,
    ) -> TranslationResponse:
        """Call one provider. ``gemini`` replaces the Gemini client when given."""
        if name == "gemini" and gemini is not None:
            return gemini(request)
        if name == "gemini":
            return self.gemini.translate(request)
        if name == "groq":
            return self.groq.translate(request)
        if name == "openrouter":
            return self.openrouter.translate(request)
        raise ProviderCallError(name, f"{name} is not a translation provider.", kind="unconfigured")

    def options(self) -> tuple[list[ModelInfo], list[ModelInfo], list[GroqSnapshot], str]:
        """Return model lists and Groq usage. Keys are not included.

        Returns:
            Groq models, OpenRouter models, one snapshot per known Groq model,
            and a catalog error string that may be empty.
        """
        now = self.clock()
        groq_models = [ModelInfo(id=model_id, name=label) for model_id, label in GROQ_MODEL_CHOICES]
        openrouter_models = [
            ModelInfo(id=model_id, name=label) for model_id, label in OPENROUTER_MODEL_CHOICES
        ]
        seen = {item.id for item in groq_models}
        snapshots = [self.groq.tracker.snapshot(item.id, self.rules, now) for item in groq_models]
        for model in self.groq.tracker.models():
            if model not in seen:
                snapshots.append(self.groq.tracker.snapshot(model, self.rules, now))
        return groq_models, openrouter_models, snapshots, ""


def _canonical_review(provider: str, text: str) -> str:
    """Return findings JSON, or raise a malformed provider error."""
    try:
        return _parse_findings(text).model_dump_json()
    except AIReviewError as error:
        raise ProviderCallError(
            provider,
            "The model returned a review that was not the expected JSON.",
            kind="malformed",
        ) from error


def _public_error(error: Exception) -> str:
    """Return a message that is safe to show. Unknown errors stay class names."""
    if isinstance(error, (ProviderCallError, AIReviewError, ProjectStateError)):
        return str(error)
    return error.__class__.__name__


def _raise_failures(failures: list[tuple[str, Exception]]) -> None:
    """Re-raise a single provider error, or name every provider that failed."""
    if len(failures) == 1:
        raise failures[0][1]
    tried = ", ".join(f"{DISPLAY[name]} ({_public_error(error)})" for name, error in failures)
    raise AIReviewError(f"Translation failed. Tried {tried}.")
