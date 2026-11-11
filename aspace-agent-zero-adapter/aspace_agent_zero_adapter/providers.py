"""Model providers — mirror of models.py, minus LiteLLM (D9).

Upstream (models.py): ``get_chat_model(provider, name)`` builds a
LiteLLM chat wrapper; ``_merge_provider_defaults`` injects an API key
from the .env when missing (``get_api_key_raw`` reads
``API_KEY_<SERVICE>`` / ``<SERVICE>_API_KEY`` / ``<SERVICE>_API_TOKEN``).

Native rule (design D9): the gateway EGM ``:31415`` is the ONLY way.
No LiteLLM, no provider key in native code. The modelPool chain from
pas 2 (02_Factory/config.json) is the route, with a 15-minute retest:
when the current link fails, fall over to the next link and record
the switch; after the retest window, the first link is tried again.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

GATEWAY_URL = "http://127.0.0.1:31415/v1/chat/completions"
MODELPOOL_CHAIN = [
    "freellmapi/auto",
    "claude-sonnet-4-5",
    "qwen3.8-max",
    "gemini-3.8-flash",
    "deepseek-v4-flash",
]
RETEST_SECONDS = 900  # 15 min, pas 2 modelPool rule


def get_api_key(service: str) -> str:
    """Upstream sentinel, kept as a refusal.

    The native provider never reads a provider key: no .env lookup,
    no environment read, no key parameter anywhere. Returns ``"None"``
    exactly as the upstream sentinel does when nothing is stored —
    except here nothing is ever stored, by construction.
    """
    return "None"


class RateLimiter:
    """Mirror of models.apply_rate_limiter's rule (upstream DOX).

    When all request, input, and output limits are unset, token
    counting is skipped and no limiter is returned (``enabled`` is
    False). Any configured limit retains normal accounting.
    """

    def __init__(self, requests: int = 0, input_tokens: int = 0, output_tokens: int = 0):
        self.limits = {
            "requests": requests or 0,
            "input": input_tokens or 0,
            "output": output_tokens or 0,
        }
        self.enabled = any(self.limits.values())
        self.counts = {"requests": 0, "input": 0, "output": 0}

    def check(self, input_tokens: int = 0, output_tokens: int = 0) -> bool:
        if not self.enabled:
            return True
        self.counts["requests"] += 1
        self.counts["input"] += input_tokens
        self.counts["output"] += output_tokens
        return (
            self.counts["requests"] <= (self.limits["requests"] or 10**9)
            and self.counts["input"] <= (self.limits["input"] or 10**9)
            and self.counts["output"] <= (self.limits["output"] or 10**9)
        )


class GatewayProvider:
    """Chat model client speaking to the EGM gateway only (H-P5-4).

    ``http_post`` is injectable for tests; the default posts JSON to
    the gateway with ``urllib`` (stdlib). No ``api_key`` parameter
    exists on this class — passing one raises, by design.
    """

    def __init__(
        self,
        endpoint: str = GATEWAY_URL,
        chain: list[str] | None = None,
        http_post=None,
        clock=None,
    ):
        self.endpoint = endpoint
        self.chain = list(chain or MODELPOOL_CHAIN)
        self._http_post = http_post or self._default_post
        self._clock = clock or time.monotonic
        self.link = 0  # index into the chain; 0 = first link
        self.switches: list[dict] = []  # failover record (receipt)
        self._link_failed_at: float | None = None

    @property
    def current_model(self) -> str:
        return self.chain[self.link]

    def _default_post(self, url: str, payload: dict) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _maybe_retest_first_link(self) -> None:
        if self.link == 0 or self._link_failed_at is None:
            return
        if self._clock() - self._link_failed_at >= RETEST_SECONDS:
            self.link = 0
            self._link_failed_at = None

    def chat(self, messages: list[dict], model: str | None = None) -> dict:
        """One chat turn through the gateway, with failover.

        Returns ``{"content": str, "model": str, "link": int}``.
        On transport failure the next link is tried and the switch
        is recorded; when the chain is exhausted the last error is
        raised. The retest window restores the first link.
        """
        if model is not None and model not in self.chain:
            raise ValueError(f"model {model!r} is not in the modelPool chain")
        self._maybe_retest_first_link()
        start_link = self.link if model is None else self.chain.index(model)
        last_error: Exception | None = None
        for offset in range(len(self.chain)):
            idx = (start_link + offset) % len(self.chain)
            payload = {
                "model": self.chain[idx],
                "messages": messages,
            }
            try:
                result = self._http_post(self.endpoint, payload)
            except Exception as exc:  # transport failure -> failover
                last_error = exc
                self.switches.append(
                    {
                        "from": self.chain[idx],
                        "to": self.chain[(idx + 1) % len(self.chain)],
                        "reason": f"{type(exc).__name__}: {exc}",
                        "at": time.time(),
                    }
                )
                if idx == 0:
                    # Arm the retest window even when a later link saves the turn.
                    self._link_failed_at = self._clock()
                continue
            content = ""
            try:
                content = result["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                content = ""
            if idx != self.link:
                self.link = idx
            if idx == 0:
                self._link_failed_at = None
            return {"content": content, "model": self.chain[idx], "link": idx}
        if self._link_failed_at is None:
            self._link_failed_at = self._clock()
        raise last_error

    def refuse_api_key(self, *_args, **_kwargs):
        """Any attempt to supply a provider key is refused (D9 OUT)."""
        raise RuntimeError(
            "provider keys are refused: the gateway :31415 is the only way (D9)"
        )
