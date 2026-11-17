"""Shared translation request and response types.

Providers return these objects. Callers do not branch on HTTP clients.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelChoice:
    """Which provider the user asked for.

    Attributes:
        mode: ``auto``, ``gemini``, ``groq``, or ``openrouter``.
        groq_model: Groq model id, or ``None`` to use the configured default.
        openrouter_model: OpenRouter model id, or ``None`` for the default.
    """

    mode: str = "auto"
    groq_model: str | None = None
    openrouter_model: str | None = None


@dataclass(frozen=True)
class TranslationRequest:
    """One provider-agnostic translation call.

    Attributes:
        prompt: The full prompt.
        purpose: ``review`` expects the AI-review JSON object. ``text`` expects
            plain model text.
        estimated_tokens: Input tokens plus reserved output tokens.
        groq_model: Groq model id to use when this request is sent to Groq.
        openrouter_model: OpenRouter model id to use for OpenRouter.
    """

    prompt: str
    purpose: str
    estimated_tokens: int = 0
    groq_model: str = ""
    openrouter_model: str = ""


@dataclass(frozen=True)
class TokenUsage:
    """Token counts reported by a provider, when it sent them.

    Attributes:
        prompt_tokens: Input tokens, if reported.
        completion_tokens: Output tokens, if reported.
        total_tokens: Sum reported by the provider, if reported.
    """

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class GroqSnapshot:
    """Rate-limit state for one Groq model.

    Attributes:
        model: Groq model id these numbers belong to.
        limit_tokens: TPM limit from ``x-ratelimit-limit-tokens``.
        remaining_tokens: TPM remaining from ``x-ratelimit-remaining-tokens``.
        reset_tokens: TPM reset delay from ``x-ratelimit-reset-tokens``.
        limit_requests: RPD limit from ``x-ratelimit-limit-requests``.
        remaining_requests: RPD remaining from ``x-ratelimit-remaining-requests``.
        reset_requests: RPD reset delay from ``x-ratelimit-reset-requests``.
        session_requests: Calls this process has made for the model.
        session_tokens: Tokens counted locally when the provider omitted usage.
        has_header_data: True after a response included at least one Groq limit header.
        low_budget: Remaining TPM or RPD is under the configured fraction.
        rate_limited_until: Monotonic-free epoch seconds; calls wait until then.
        warning: Short warning for the UI, or an empty string.
    """

    model: str
    limit_tokens: int | None = None
    remaining_tokens: int | None = None
    reset_tokens: str | None = None
    limit_requests: int | None = None
    remaining_requests: int | None = None
    reset_requests: str | None = None
    session_requests: int = 0
    session_tokens: int = 0
    has_header_data: bool = False
    low_budget: bool = False
    rate_limited_until: float | None = None
    warning: str = ""


@dataclass
class TranslationResponse:
    """Text from one provider, plus whatever usage that provider reported.

    Attributes:
        text: Model text. For ``purpose="review"`` this is the findings JSON.
        provider: ``gemini``, ``groq``, or ``openrouter``.
        model: Model id that produced ``text``.
        routing_note: Why this provider was chosen, including any fallback.
        usage: Provider token usage, when the body included it.
        rate_limit_state: Latest Groq snapshot for the Groq model on the request.
    """

    text: str
    provider: str
    model: str
    routing_note: str = ""
    usage: TokenUsage | None = None
    rate_limit_state: GroqSnapshot | None = None


@dataclass(frozen=True)
class RoutePlan:
    """The providers to try, in order, and the note the UI should show.

    Attributes:
        providers: Provider keys, first choice first. Gemini is last when a
            fallback exists.
        reason: The routing decision, without fallback notes.
        limit_message: Set when an explicit OpenRouter choice is already over
            the local cap and must not be sent.
    """

    providers: tuple[str, ...]
    reason: str
    limit_message: str | None = None


@dataclass(frozen=True)
class ModelInfo:
    """One model in a provider dropdown.

    Attributes:
        id: Provider model id sent back on a later request.
        name: Label shown in the dropdown.
    """

    id: str
    name: str


class ProviderCallError(Exception):
    """A provider failed in a way the router may fall back from.

    Attributes:
        provider: ``groq``, ``openrouter``, or ``gemini``.
        kind: ``timeout``, ``server``, ``http``, ``malformed``, ``rate_limit``,
            ``limited``, or ``unconfigured``.
        headers: Response headers when the failure was an HTTP response.
    """

    def __init__(
        self,
        provider: str,
        message: str,
        *,
        kind: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Store the provider, the kind of failure, and any response headers.

        Args:
            provider: ``groq``, ``openrouter``, or ``gemini``.
            message: Text safe to show in the UI. Must not contain an API key.
            kind: ``timeout``, ``server``, ``http``, ``malformed``, ``rate_limit``,
                ``limited``, or ``unconfigured``.
            headers: Response headers, when this failure was an HTTP response.
        """
        super().__init__(message)
        self.provider = provider
        self.kind = kind
        self.headers = headers or {}
