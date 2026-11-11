# A'Space Agent Zero Adapter — DOX

## Purpose

- A'Space-native re-implementation of the agent-zero engine functions
  (D-N051 F8 pas 5), as a sidecar to the gel, never a patch of it.
- The adapter is the proof that the engine runs without the fork:
  loop, provider, memory, job loop, plugin triage, lineage pins.

## Ownership

- `aspace_agent_zero_adapter/agent_loop.py` owns the Agent loop
  (mirror of `agent.py:364` `Agent.monologue`).
- `aspace_agent_zero_adapter/providers.py` owns the model client:
  gateway EGM `:31415` only, modelPool chain, no LiteLLM, no keys.
- `aspace_agent_zero_adapter/memory.py` owns unified memory:
  Shared Brain JSONL is the only source of truth; FAISS is a derived
  index, rebuilt from the brain, never the inverse.
- `aspace_agent_zero_adapter/job_loop.py` owns the scheduler as the
  daemon job loop. No cron is accepted anywhere.
- `aspace_agent_zero_adapter/plugins.py` owns the 47-plugin triage
  (35 ported / 9 surfaces / 3 abandoned) and the native registry.
- `aspace_agent_zero_adapter/lineage.py` owns the gel checks (H-M1,
  H-M2) and the 10 upstream surface pins (H-P5-1).
- `contract.json` is the adapter's public contract (gel, pin, family,
  owner, endpoints, triage summary).

## Local Contracts

- Python stdlib only. No dependency is added to the fork.
- The adapter never imports the fork (`agent.py`, `models.py`,
  `helpers/`, `plugins/`). It mirrors them.
- No provider key is read, stored, or accepted anywhere. The gateway
  `:31415` is the only way (design D9).
- No cron syntax is accepted: `create_task` and `update_task` raise
  on any `cron` argument (design D7).
- Message-loop completion requires an explicit response-tool call
  with `break_loop`. Free text remains generation thoughts and
  silently continues; never synthesize a response-tool call from
  prose. Malformed tool intent keeps its repair path.
- `hist_add_ai_response` owns Responses-API state advancement
  internally; callers never invoke the remembering step manually.
- `contract.json` is updated only when the gel, the pin, or the
  triage changes, and the change is named in the commit message.

## Verification

- Run the adapter suite from the fork root, with the pas-5 venv:
  `~/workspace/.venvs-dn053/agent-zero/bin/python -m pytest aspace-agent-zero-adapter/tests -v`
- The fork's own suite is NOT run here: its 245 test files require
  litellm, langchain, flask, faiss-cpu and the full requirements
  stack, which is not installed on this VM. That is a named reserve
  (R-A1), not a green light.
- After every meaningful change, re-run the adapter suite and update
  this file and `README.md` if a contract moved.
