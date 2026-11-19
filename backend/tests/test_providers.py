"""Routing, Groq headers, OpenRouter limits, and fallback. No live API calls."""

import json

import pytest

from legacylift.cobol.ai_review import ProgramFindings
from legacylift.errors import AIReviewError, ProviderLimitError
from legacylift.providers.config import RoutingRules
from legacylift.providers.estimate import estimate_input_tokens, estimate_total, format_tokens
from legacylift.providers.gemini import GeminiProvider
from legacylift.providers.groq import (
    GroqProvider,
    GroqUsageTracker,
    parse_duration,
    parse_groq_headers,
)
from legacylift.providers.http import HttpFailure, HttpResult
from legacylift.providers.openrouter import ModelCatalog, OpenRouterProvider, SlidingWindowLimiter
from legacylift.providers.router import Translator, fallback_chain, plan_route
from legacylift.providers.types import (
    GroqSnapshot,
    ModelChoice,
    TranslationRequest,
    TranslationResponse,
)

RULES = RoutingRules(
    groq_per_request_token_limit=100,
    gemini_token_threshold=40,
    low_budget_fraction=0.15,
    openrouter_requests_per_minute=20,
    openrouter_requests_per_day=50,
    groq_retry_max_seconds=1,
)
NOW = 1_700_000_000.0


def test_estimate_uses_the_named_divisor_and_reserves_output():
    assert estimate_input_tokens("") == 0
    assert estimate_input_tokens("a" * 7, chars_per_token=3.5) == 2
    rules = RoutingRules(chars_per_token=3.5, output_token_ratio=1)
    assert estimate_total("a" * 7, rules) == 4
    assert format_tokens(1200) == "1.2k"
    assert format_tokens(999) == "999"


def _plan(
    tokens: int,
    mode: str = "auto",
    *,
    groq: bool = True,
    openrouter: bool = True,
    state: GroqSnapshot | None = None,
    block: str | None = None,
) -> str:
    plan = plan_route(
        estimated_tokens=tokens,
        choice=ModelChoice(mode=mode, groq_model="openai/gpt-oss-20b"),
        rules=RULES,
        groq_configured=groq,
        openrouter_configured=openrouter,
        groq_state=state,
        openrouter_block=block,
        now=NOW,
    )
    return (
        f"{plan.providers[0]}|{plan.reason}|{plan.limit_message or ''}|{','.join(plan.providers)}"
    )


def test_routing_sends_large_estimates_to_gemini():
    per_request = _plan(101)
    assert per_request.startswith("gemini|")
    assert "per-request limit" in per_request
    assert per_request.endswith("|gemini")
    threshold = _plan(41)
    assert "routing threshold" in threshold
    assert threshold.endswith("|gemini")


def test_routing_sends_a_small_estimate_to_groq_with_budget():
    state = GroqSnapshot(
        model="openai/gpt-oss-20b",
        limit_tokens=8000,
        remaining_tokens=7000,
        limit_requests=1000,
        remaining_requests=900,
        has_header_data=True,
    )
    decision = _plan(20, state=state)
    assert decision.startswith("groq|")
    assert "within remaining TPM" in decision
    assert "1" in decision or "20" in decision


def test_routing_allows_groq_before_any_headers():
    decision = _plan(20, state=GroqSnapshot(model="openai/gpt-oss-20b"))
    assert decision.startswith("groq|")
    assert "no rate-limit data yet" in decision


def test_routing_leaves_groq_when_the_budget_is_exhausted_or_low():
    exhausted = GroqSnapshot(
        model="openai/gpt-oss-20b",
        limit_tokens=8000,
        remaining_tokens=10,
        limit_requests=1000,
        remaining_requests=0,
        has_header_data=True,
    )
    assert _plan(20, state=exhausted).startswith("openrouter|")
    assert "RPD is exhausted" in _plan(20, state=exhausted)
    low = GroqSnapshot(
        model="openai/gpt-oss-20b",
        limit_tokens=8000,
        remaining_tokens=1000,
        limit_requests=1000,
        remaining_requests=100,
        has_header_data=True,
    )
    assert "below 15%" in _plan(20, state=low)
    assert _plan(20, state=low, openrouter=False).startswith("gemini|")
    assert "OpenRouter is not configured" in _plan(20, state=low, openrouter=False)
    assert _plan(20, groq=False, openrouter=False).startswith("gemini|")


def test_routing_skips_a_rate_limited_groq_model():
    state = GroqSnapshot(
        model="openai/gpt-oss-20b",
        has_header_data=True,
        limit_tokens=8000,
        remaining_tokens=7000,
        limit_requests=1000,
        remaining_requests=900,
        rate_limited_until=NOW + 30,
    )
    assert "rate-limited" in _plan(20, state=state)


def test_manual_choice_overrides_auto():
    assert _plan(500, "gemini").startswith("gemini|")
    assert "selected" in _plan(5, "groq")
    assert _plan(5, "groq", groq=False, openrouter=False).split("|")[-1] == "groq,gemini"
    blocked = plan_route(
        estimated_tokens=5,
        choice=ModelChoice(mode="openrouter"),
        rules=RULES,
        groq_configured=True,
        openrouter_configured=True,
        groq_state=None,
        openrouter_block="OpenRouter limit reached: maximum of 20 requests per minute.",
        now=NOW,
    )
    assert blocked.limit_message is not None
    assert fallback_chain("groq", groq_configured=True, openrouter_configured=False) == (
        "groq",
        "gemini",
    )


def test_parse_groq_headers_and_durations():
    parsed = parse_groq_headers(
        {
            "X-RateLimit-Limit-Tokens": "18000",
            "x-ratelimit-remaining-tokens": "17997",
            "x-ratelimit-reset-tokens": "7.66s",
            "x-ratelimit-limit-requests": "14400",
            "x-ratelimit-remaining-requests": "14370",
            "x-ratelimit-reset-requests": "2m59.56s",
        }
    )
    assert parsed.any_present is True
    assert (parsed.limit_tokens, parsed.remaining_tokens, parsed.reset_tokens) == (
        18000,
        17997,
        "7.66s",
    )
    assert parsed.limit_requests == 14400
    assert parsed.remaining_requests == 14370
    assert parse_duration("7.66s") == pytest.approx(7.66)
    assert parse_duration("2m59.56s") == pytest.approx(179.56)
    assert parse_duration("not-a-duration") is None
    missing = parse_groq_headers({})
    assert missing.any_present is False
    assert missing.limit_tokens is None
    assert missing.remaining_requests is None


def test_groq_tracker_keeps_a_session_count_without_headers():
    tracker = GroqUsageTracker()
    before = tracker.snapshot("openai/gpt-oss-20b", RULES, NOW)
    assert before.has_header_data is False
    assert before.session_requests == 0
    tracker.observe("openai/gpt-oss-20b", {}, tokens=12, rules=RULES, now=NOW)
    after = tracker.snapshot("openai/gpt-oss-20b", RULES, NOW)
    assert after.has_header_data is False
    assert (after.session_requests, after.session_tokens) == (1, 12)


def test_groq_429_retries_once_when_the_hint_is_short_and_not_when_it_is_long():
    sleeps: list[float] = []
    calls = {"n": 0}

    def transport(request, timeout):
        assert "secret-groq" not in request.full_url
        assert request.get_header("Authorization") == "Bearer secret-groq"
        calls["n"] += 1
        if calls["n"] == 1:
            raise HttpFailure(
                "The provider returned HTTP 429.",
                kind="rate_limit",
                status=429,
                headers={"retry-after": "0.25"},
            )
        return HttpResult(
            200,
            json.dumps({"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 4}}),
            {"x-ratelimit-remaining-tokens": "10", "x-ratelimit-limit-tokens": "100"},
        )

    provider = GroqProvider(
        "secret-groq",
        timeout=5,
        rules=RULES,
        transport=transport,
        clock=lambda: NOW,
        sleep=sleeps.append,
    )
    response = provider.translate(TranslationRequest("hello", "text", 4, "openai/gpt-oss-20b", ""))
    assert sleeps == [0.25]
    assert calls["n"] == 2
    assert response.rate_limit_state is not None
    assert response.rate_limit_state.remaining_tokens == 10
    assert response.rate_limit_state.low_budget is True

    calls["n"] = 0

    def slow(request, timeout):
        calls["n"] += 1
        raise HttpFailure(
            "The provider returned HTTP 429.",
            kind="rate_limit",
            status=429,
            headers={"retry-after": "30", "x-ratelimit-reset-requests": "2m59.56s"},
        )

    limited = GroqProvider(
        "secret-groq",
        timeout=5,
        rules=RULES,
        transport=slow,
        clock=lambda: NOW,
        sleep=sleeps.append,
    )
    with pytest.raises(Exception, match="rate limit") as caught:
        limited.translate(TranslationRequest("hello", "text", 4, "openai/gpt-oss-20b", ""))
    assert calls["n"] == 1
    assert sleeps == [0.25]
    snapshot = limited.tracker.snapshot("openai/gpt-oss-20b", RULES, NOW)
    assert snapshot.rate_limited_until == pytest.approx(NOW + 30)
    assert caught.value.kind == "rate_limit"


def test_openrouter_sliding_window_blocks_the_minute_and_the_day():
    limiter = SlidingWindowLimiter(per_minute=20, per_day=50)
    for offset in range(20):
        assert limiter.acquire(NOW + offset / 100) is None
    minute = limiter.acquire(NOW + 0.5)
    assert minute is not None
    assert "20 requests per minute" in minute
    assert "Try again in" in minute
    assert limiter.acquire(NOW + 61) is None

    daily = SlidingWindowLimiter(per_minute=100, per_day=50)
    for index in range(50):
        assert daily.acquire(NOW + index) is None
    blocked = daily.status(NOW + 50)
    assert blocked is not None
    assert "50 requests per day" in blocked
    assert daily.status(NOW + 86_400 + 1) is None


def test_openrouter_does_not_call_http_when_the_window_is_full():
    calls = {"n": 0}

    def transport(request, timeout):
        calls["n"] += 1
        raise AssertionError("the request must not be sent")

    provider = OpenRouterProvider(
        "secret-open",
        timeout=5,
        rules=RULES,
        limiter=SlidingWindowLimiter(per_minute=1, per_day=50),
        transport=transport,
        clock=lambda: NOW,
    )
    provider.limiter.acquire(NOW)
    with pytest.raises(Exception, match="20 requests per minute|1 request"):
        provider.translate(TranslationRequest("hello", "text", 4, "", "openrouter/auto"))
    assert calls["n"] == 0


def test_review_facts_drop_the_planning_monologue():
    from legacylift.providers.openrouter import _review_facts

    text = _review_facts(
        "We need to compare the sources. Need to be careful. "
        "COBOL line 9 DISPLAY prints the name. Python line 4 uses print."
    )
    assert "Need to" not in text
    assert "DISPLAY prints the name" in text


def test_openrouter_converts_reasoning_into_review_json():
    calls = {"n": 0}

    def transport(request, timeout):
        calls["n"] += 1
        sent = json.loads(request.data.decode())
        if calls["n"] == 1:
            body = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "reasoning": "DISPLAY maps to print.",
                        }
                    }
                ]
            }
        else:
            assert "DISPLAY maps to print." in sent["messages"][0]["content"]
            body = {"choices": [{"message": {"content": '{"matches":[],"concerns":[]}'}}]}
        return HttpResult(200, json.dumps(body), {})

    provider = OpenRouterProvider(
        "secret-open", timeout=5, rules=RULES, transport=transport, clock=lambda: NOW
    )
    response = provider.translate(
        TranslationRequest("Compare COBOL and Python.", "review", openrouter_model="baidu/ernie")
    )
    assert calls["n"] == 2
    assert '"matches"' in response.text


def _translator(
    groq_transport, openrouter_transport, *, groq_key="secret-groq", open_key="secret-open"
):
    rules = RULES
    tracker = GroqUsageTracker()
    groq = GroqProvider(
        groq_key,
        timeout=5,
        rules=rules,
        tracker=tracker,
        transport=groq_transport,
        clock=lambda: NOW,
    )
    openrouter = OpenRouterProvider(
        open_key,
        timeout=5,
        rules=rules,
        transport=openrouter_transport,
        clock=lambda: NOW,
    )
    catalog = ModelCatalog(rules, transport=openrouter_transport)
    translator = Translator(
        gemini=GeminiProvider("secret-gemini", timeout=5, rules=rules),
        groq=groq,
        openrouter=openrouter,
        catalog=catalog,
        rules=rules,
        clock=lambda: NOW,
    )
    return translator


def _chat(text: str) -> HttpResult:
    return HttpResult(200, json.dumps({"choices": [{"message": {"content": text}}]}), {})


def _review_json() -> str:
    return ProgramFindings(matches=[], concerns=[]).model_dump_json()


def test_fallback_order_skips_a_timeout_then_a_server_error():
    def groq_down(request, timeout):
        raise HttpFailure("The request timed out.", kind="timeout")

    def open_ok(request, timeout):
        return _chat(_review_json())

    gemini_calls = {"n": 0}

    def gemini(request):
        gemini_calls["n"] += 1
        return TranslationResponse(
            text=_review_json(), provider="gemini", model="gemini-3.5-flash-lite"
        )

    first = _translator(groq_down, open_ok).translate(
        TranslationRequest("short", "review"),
        ModelChoice("auto"),
        gemini=gemini,
    )
    assert first.provider == "openrouter"
    assert "Fell back from Groq" in first.routing_note
    assert "Fell back to OpenRouter" in first.routing_note
    assert gemini_calls["n"] == 0

    def open_down(request, timeout):
        raise HttpFailure("The provider returned HTTP 503.", kind="server", status=503)

    second = _translator(groq_down, open_down).translate(
        TranslationRequest("short", "review"),
        ModelChoice("auto"),
        gemini=gemini,
    )
    assert second.provider == "gemini"
    assert "Fell back to Gemini" in second.routing_note
    assert gemini_calls["n"] == 1


def test_malformed_provider_text_falls_back_and_all_failures_are_named():
    def groq_transport(request, timeout):
        return _chat("not json")

    def open_transport(request, timeout):
        raise HttpFailure("The provider returned HTTP 500.", kind="server", status=500)

    translator = _translator(groq_transport, open_transport)

    def gemini(request):
        raise AIReviewError("Gemini rejected the AI review request.")

    with pytest.raises(AIReviewError, match="Groq") as caught:
        translator.translate(
            TranslationRequest("short", "review"), ModelChoice("auto"), gemini=gemini
        )
    message = str(caught.value)
    assert "OpenRouter" in message
    assert "Gemini" in message
    assert "secret" not in message


def test_explicit_openrouter_limit_is_not_sent():
    def transport(request, timeout):
        raise AssertionError("the request must not be sent")

    translator = _translator(transport, transport)
    for _ in range(20):
        translator.openrouter.limiter.acquire(NOW)
    with pytest.raises(ProviderLimitError, match="20 requests per minute"):
        translator.translate(
            TranslationRequest("short", "text"),
            ModelChoice("openrouter", openrouter_model="openrouter/auto"),
        )


def test_model_catalog_reuses_a_list_until_the_ttl():
    calls = {"n": 0}

    def transport(request, timeout):
        calls["n"] += 1
        assert "secret-groq" not in request.full_url
        return HttpResult(
            200, json.dumps({"data": [{"id": "openai/gpt-oss-20b", "name": "GPT"}]}), {}
        )

    catalog = ModelCatalog(RoutingRules(model_catalog_ttl_seconds=10), transport=transport)
    first, error = catalog.groq_models("secret-groq", 100)
    second, _ = catalog.groq_models("secret-groq", 105)
    assert error == ""
    assert first == second
    assert calls["n"] == 1
    catalog.groq_models("secret-groq", 120)
    assert calls["n"] == 2
    assert first[0].id == "openai/gpt-oss-20b"


def test_options_endpoint_discloses_caps_and_hides_keys(tmp_path):
    from helpers import make_client

    client = make_client(tmp_path, groq_api_key="secret-groq", openrouter_api_key="secret-open")

    response = client.get("/api/providers/options")
    assert response.status_code == 200
    assert "secret" not in response.text
    body = response.json()
    assert body["gemini_model"] == "gemini-3.5-flash-lite"
    assert body["groq_configured"] is True
    assert body["openrouter_configured"] is True
    assert body["openrouter_requests_per_day"] == 50
    assert body["openrouter_requests_per_minute"] == 20
    assert [item["id"] for item in body["groq_models"]] == [
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
    ]
    assert [item["id"] for item in body["openrouter_models"]] == [
        "baidu/ernie-5.5-flash-preview-20261110:free",
        "nvidia/nemotron-3.5-lightning-20260807:free",
        "cohere/north-mini-code-20260617:free",
        "nvidia/nemotron-3-ultra-550b-a55b-20260604:free",
        "google/gemma-4-31b-it-20260402:free",
    ]


def test_gemini_provider_uses_the_existing_review_client(monkeypatch):
    captured = {}

    def fake(prompt, *, api_key, timeout):
        captured["url_key"] = api_key
        captured["timeout"] = timeout
        assert "secret-gemini" not in prompt
        return ProgramFindings(matches=[], concerns=[])

    monkeypatch.setattr("legacylift.providers.gemini.request_gemini_review", fake)
    response = GeminiProvider("secret-gemini", timeout=5, rules=RULES).translate(
        TranslationRequest("COBOL", "review")
    )
    assert response.provider == "gemini"
    assert response.model == "gemini-3.5-flash-lite"
    assert captured == {"url_key": "secret-gemini", "timeout": 5}
