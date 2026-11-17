"""Model lists and Groq usage.

``GET /api/providers/options`` feeds the model selector. The response includes
OpenRouter's configured caps and never includes an API key.
"""

from dataclasses import asdict

from fastapi import APIRouter, Request

from legacylift.providers.router import Translator
from legacylift.schemas import GroqUsageResponse, ProviderModelResponse, ProviderOptionsResponse

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("/options")
def provider_options(request: Request) -> ProviderOptionsResponse:
    """List selectable models and the current Groq usage.

    OpenRouter's daily and per-minute caps are included so the UI can disclose
    them. Groq usage is empty of header data until Groq has answered a call.

    \f
    Returns:
        Model lists, caps, and Groq snapshots.
    """
    translator: Translator = request.app.state.translator
    groq_models, openrouter_models, snapshots, error = translator.options()
    rules = translator.rules
    return ProviderOptionsResponse(
        gemini_model=rules.gemini_model,
        groq_configured=translator.groq.api_key is not None,
        openrouter_configured=translator.openrouter.api_key is not None,
        groq_models=[ProviderModelResponse(id=item.id, name=item.name) for item in groq_models],
        openrouter_models=[ProviderModelResponse(id=item.id, name=item.name) for item in openrouter_models],
        openrouter_requests_per_day=rules.openrouter_requests_per_day,
        openrouter_requests_per_minute=rules.openrouter_requests_per_minute,
        low_budget_fraction=rules.low_budget_fraction,
        groq_usage=[GroqUsageResponse.model_validate(asdict(item)) for item in snapshots],
        catalog_error=error,
    )
