"""Limits, thresholds, and routing rules for translation providers.

Every number the router and the limiters consult lives here. API keys do not:
those stay in ``LEGACYLIFT_*`` environment variables read by ``legacylift.config``.

The Groq per-request figure and the OpenRouter 50/day and 20/minute figures need
confirmation. They are defaults, not measurements from this deployment.
"""

from dataclasses import dataclass

from legacylift.cobol.ai_review import GEMINI_MODEL

# Conservative character estimate. The repo has no tokenizer.
CHARS_PER_TOKEN = 3.5
# Translation output is roughly proportional to the input, so reserve this
# multiple of the input estimate for the completion.
OUTPUT_TOKEN_RATIO = 1.0


@dataclass(frozen=True)
class RoutingRules:
    """Numbers that decide which provider handles one translation request.

    Attributes:
        chars_per_token: Divisor for the character-based token estimate.
        output_token_ratio: Extra tokens reserved for the completion, as a
            multiple of the input estimate.
        groq_per_request_token_limit: Estimated input plus reserved output above
            this cannot be sent to Groq. Confirm against the account's TPM.
            ``8000`` matches the published developer-plan TPM for
            ``openai/gpt-oss-20b`` on Groq's rate-limit page (fetched
            2026-11-16). Live TPM still comes from response headers.
        gemini_token_threshold: Estimated totals above this route to Gemini
            even when they are under the Groq per-request limit.
        low_budget_fraction: Remaining TPM or RPD under this share of the limit
            warns the UI and makes auto mode skip Groq.
        openrouter_requests_per_day: Client-side daily cap. Confirm with
            OpenRouter; this app does not read an OpenRouter usage API.
        openrouter_requests_per_minute: Client-side per-minute cap. Confirm
            with OpenRouter.
        model_catalog_ttl_seconds: How long a fetched model list is reused.
        catalog_timeout_seconds: How long a model-list request may wait.
        groq_retry_max_seconds: A 429 is retried once only when the hint is at
            most this many seconds. Longer waits fall back instead of sleeping.
        gemini_model: The existing Gemini model id.
        default_groq_model: Groq model used when the user has not picked one.
            One of :data:`GROQ_MODEL_CHOICES`.
        default_openrouter_model: OpenRouter model used when the user has not
            picked one. One of :data:`OPENROUTER_MODEL_CHOICES`.
    """

    chars_per_token: float = CHARS_PER_TOKEN
    output_token_ratio: float = OUTPUT_TOKEN_RATIO
    groq_per_request_token_limit: int = 8_000
    gemini_token_threshold: int = 6_000
    low_budget_fraction: float = 0.15
    openrouter_requests_per_day: int = 50
    openrouter_requests_per_minute: int = 20
    model_catalog_ttl_seconds: int = 900
    catalog_timeout_seconds: float = 10.0
    groq_retry_max_seconds: float = 1.0
    gemini_model: str = GEMINI_MODEL
    default_groq_model: str = "qwen/qwen3.8-27b"
    default_openrouter_model: str = "baidu/ernie-5.5-flash-preview-20261110:free"


# The Groq dropdown is this list, not the full models endpoint.
GROQ_MODEL_CHOICES: tuple[tuple[str, str], ...] = (
    ("qwen/qwen3.8-27b", "qwen/qwen3.8-27b"),
    ("openai/gpt-oss-120b", "openai/gpt-oss-120b"),
)

# The OpenRouter dropdown is this list. Each id is a free model.
OPENROUTER_MODEL_CHOICES: tuple[tuple[str, str], ...] = (
    ("baidu/ernie-5.5-flash-preview-20261110:free", "Baidu: ERNIE-5.5-Flash-Preview (free)"),
    ("nvidia/nemotron-3.5-lightning-20260807:free", "NVIDIA: Nemotron 3.5 Lightning (free)"),
    ("cohere/north-mini-code-20260617:free", "Cohere: North Mini Code (free)"),
    (
        "nvidia/nemotron-3-ultra-550b-a55b-20260604:free",
        "NVIDIA: Nemotron 3 Ultra 550B (free)",
    ),
    ("google/gemma-4-31b-it-20260402:free", "Google: Gemma 4 31B (free)"),
)

ROUTING_RULES = RoutingRules()
