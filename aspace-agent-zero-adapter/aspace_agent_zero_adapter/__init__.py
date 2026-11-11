"""A'Space OS V5 — Agent Zero adapter (D-N051 F8 pas 5).

Re-implementation of the agent-zero engine functions as A'Space-native
code (Python, stdlib only), mirroring the gel (ba9b67d):

- agent_loop  — the Agent loop (agent.py:364 Agent.monologue):
  message -> model -> tools -> memory -> response.
- providers   — the model provider client (models.py get_chat_model):
  gateway EGM :31415 only, modelPool chain, NO LiteLLM, NO provider keys.
- memory      — unified memory (D6): Shared Brain JSONL is the single
  source of truth; FAISS is a derived retrieval index, never the inverse.
- job_loop    — the scheduler as the daemon job loop (D7): scheduled /
  adhoc / planned tasks, proof by receipt, NO cron.
- plugins     — the 47-plugin triage (D5): 35 ported / 9 surfaces / 3
  abandoned, verified against the gel.
- lineage     — H-M1/H-M2 checks + 10 upstream surface pins.

This is by an automated agent, not a human.
"""

from .agent_loop import AspaceAgentLoop, LoopState, extract_tool_request, validate_tool_request
from .providers import GatewayProvider, RateLimiter, get_api_key, MODELPOOL_CHAIN, GATEWAY_URL
from .memory import SharedBrainMemory, FaissIndex, check_no_divergence
from .job_loop import JobLoop, TaskKind
from .plugins import (
    ABANDONED,
    PLUGIN_TRIAGE,
    PORTED,
    SURFACES,
    PluginRegistry,
    verify_triage,
)
from .lineage import verify_gel_lineage, check_upstream_surface

__all__ = [
    "AspaceAgentLoop", "LoopState", "extract_tool_request", "validate_tool_request",
    "GatewayProvider", "RateLimiter", "get_api_key", "MODELPOOL_CHAIN", "GATEWAY_URL",
    "SharedBrainMemory", "FaissIndex", "check_no_divergence",
    "JobLoop", "TaskKind",
    "PLUGIN_TRIAGE", "PORTED", "SURFACES", "ABANDONED", "PluginRegistry", "verify_triage",
    "verify_gel_lineage", "check_upstream_surface",
]

__version__ = "0.1.0"
