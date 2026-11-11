"""Providers — gateway only, modelPool failover, no keys (H-P5-4, D9)."""

import inspect
import urllib.error

import pytest

from aspace_agent_zero_adapter import (
    GATEWAY_URL,
    MODELPOOL_CHAIN,
    GatewayProvider,
    RateLimiter,
    get_api_key,
)


def _ok_response(model):
    return lambda url, payload: {
        "choices": [{"message": {"content": f"answer from {payload['model']}"}}]
    }


def test_chain_is_the_pas2_modelpool_chain():
    assert MODELPOOL_CHAIN == [
        "freellmapi/auto",
        "claude-sonnet-4-5",
        "qwen3.8-max",
        "gemini-3.8-flash",
        "deepseek-v4-flash",
    ]
    assert GATEWAY_URL == "http://127.0.0.1:31415/v1/chat/completions"


def test_first_link_is_used_when_healthy():
    provider = GatewayProvider(http_post=_ok_response("freellmapi/auto"))
    result = provider.chat([{"role": "user", "content": "hi"}])
    assert result["model"] == "freellmapi/auto"
    assert result["link"] == 0
    assert result["content"] == "answer from freellmapi/auto"
    assert provider.switches == []


def test_failover_to_next_link_and_switch_recorded():
    def failing_first(url, payload):
        if payload["model"] == "freellmapi/auto":
            raise urllib.error.URLError("connection refused")
        return {"choices": [{"message": {"content": "fallback answer"}}]}

    provider = GatewayProvider(http_post=failing_first)
    result = provider.chat([{"role": "user", "content": "hi"}])
    assert result["model"] == "claude-sonnet-4-5"
    assert result["link"] == 1
    assert len(provider.switches) == 1
    assert provider.switches[0]["from"] == "freellmapi/auto"
    assert provider.switches[0]["to"] == "claude-sonnet-4-5"


def test_retest_first_link_after_15_minutes():
    clock = {"now": 0.0}

    def failing_first(url, payload):
        if payload["model"] == "freellmapi/auto":
            raise urllib.error.URLError("connection refused")
        return {"choices": [{"message": {"content": "ok"}}]}

    provider = GatewayProvider(http_post=failing_first, clock=lambda: clock["now"])
    provider.chat([{"role": "user", "content": "hi"}])
    assert provider.link == 1
    # Within the window: still on the second link.
    provider.chat([{"role": "user", "content": "hi"}])
    assert provider.link == 1
    # After 900 s: the first link is retried (and fails again here),
    # so one more failover is recorded: 2 in total.
    clock["now"] = 901.0
    provider.chat([{"role": "user", "content": "hi"}])
    assert len(provider.switches) == 2
    assert provider.link == 1  # back on the second link after re-failing


def test_chain_exhausted_raises_last_error():
    def always_fail(url, payload):
        raise urllib.error.URLError("down")

    provider = GatewayProvider(http_post=always_fail)
    with pytest.raises(urllib.error.URLError):
        provider.chat([{"role": "user", "content": "hi"}])
    assert len(provider.switches) == len(MODELPOOL_CHAIN)


def test_model_outside_chain_is_refused():
    provider = GatewayProvider(http_post=_ok_response("x"))
    with pytest.raises(ValueError):
        provider.chat([{"role": "user", "content": "hi"}], model="gpt-5")


def test_no_api_key_parameter_anywhere():
    sig = inspect.signature(GatewayProvider.__init__)
    assert "api_key" not in sig.parameters
    sig_chat = inspect.signature(GatewayProvider.chat)
    assert "api_key" not in sig_chat.parameters
    assert get_api_key("openai") == "None"


def test_refuse_api_key():
    provider = GatewayProvider(http_post=_ok_response("x"))
    with pytest.raises(RuntimeError, match="gateway :31415"):
        provider.refuse_api_key("sk-secret")


def test_rate_limiter_skipped_when_unset():
    limiter = RateLimiter()
    assert limiter.enabled is False
    assert limiter.check(input_tokens=10**9) is True
    limiter2 = RateLimiter(requests=1)
    assert limiter2.enabled is True
    assert limiter2.check() is True
    assert limiter2.check() is False
