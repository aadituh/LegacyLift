"""Gemini translation provider.

Review calls go through ``request_gemini_review``, which is the existing Gemini
HTTP client. Description calls go through ``describe.complete``, the existing
google-genai client. Neither request is rebuilt here.
"""

from legacylift.cobol.ai_review import request_gemini_review
from legacylift.cobol.describe import complete
from legacylift.errors import AIReviewError, ProjectStateError
from legacylift.providers.config import RoutingRules
from legacylift.providers.types import ProviderCallError, TranslationRequest, TranslationResponse


class GeminiProvider:
    """The existing Gemini model behind :meth:`translate`.

    Attributes:
        name: Always ``gemini``.
        api_key: ``LEGACYLIFT_GEMINI_API_KEY``, or ``None`` when unset.
    """

    name = "gemini"

    def __init__(self, api_key: str | None, *, timeout: float, rules: RoutingRules) -> None:
        """Store the key and the timeout the existing clients already use.

        Args:
            api_key: Gemini key. Blank is treated as unset.
            timeout: Seconds ``request_gemini_review`` may wait.
            rules: Supplies the Gemini model id.
        """
        self.api_key = api_key.strip() if api_key and api_key.strip() else None
        self.timeout = timeout
        self.rules = rules

    def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Translate ``request`` with the existing Gemini client for its purpose.

        Args:
            request: ``purpose="review"`` uses the AI-review client.
                ``purpose="text"`` uses the description client.

        Returns:
            The model text. Review text is the findings JSON.

        Raises:
            ProviderCallError: The key is unset, or the existing client failed.
        """
        if self.api_key is None:
            raise ProviderCallError(
                "gemini",
                "Set LEGACYLIFT_GEMINI_API_KEY before requesting an AI review.",
                kind="unconfigured",
            )
        if request.purpose == "review":
            try:
                findings = request_gemini_review(
                    request.prompt, api_key=self.api_key, timeout=self.timeout
                )
            except AIReviewError as error:
                raise ProviderCallError("gemini", str(error), kind="http") from error
            return TranslationResponse(
                text=findings.model_dump_json(),
                provider="gemini",
                model=self.rules.gemini_model,
            )
        try:
            text = complete(request.prompt, self.api_key)
        except ProjectStateError as error:
            raise ProviderCallError("gemini", str(error), kind="malformed") from error
        return TranslationResponse(text=text, provider="gemini", model=self.rules.gemini_model)
