# A'Space Agent Zero Adapter — D-N051 F8 pas 5

This is by an automated agent, not a human.

Adapter of **agent-zero, the heart** — the A'Space-native engine that
replaces the fork's engine functions, one by one, without ever
patching the fork.

## Anchors

| Item | Value |
|---|---|
| Fork | `Amdkn/agent-zero` ← `agent0ai/agent-zero` |
| Gel | `ba9b67df0f54ac78106ae85c552ef5d2458f7c9a` (fork main HEAD = upstream main HEAD, compare identical, drift 0) |
| Pin | `176d23f` = bind, 1 file `aspace-plugin.json`, parent `ba9b67d` |
| Plugin | `@aspace-v5/agent-zero` |
| Family | `CORE_A0_KERNEL` |
| Owner | `A0-AMADEUS / S1-RICK` |
| Fractal layer | 2L |
| Licence | MIT (file) |
| State | 0 → 2 (at integration) |
| Plugins at gel | 47 directories, `_a0_connector` present |

## What the adapter is

Python, stdlib only, in `aspace_agent_zero_adapter/`:

| Module | Mirrors (gel) | Native rule |
|---|---|---|
| `agent_loop.py` | `agent.py:364` `Agent` | message → model → tools → memory → response; completion only on explicit `break_loop` |
| `providers.py` | `models.py` `get_chat_model` | gateway EGM `:31415` only; modelPool chain; **no LiteLLM, no provider key** (D9) |
| `memory.py` | `helpers/vector_db.py` `MyFaiss` | Shared Brain JSONL is the only truth; FAISS = derived index (D6) |
| `job_loop.py` | `plugins/_scheduler` `SchedulerTool` | the scheduler IS the job loop; **no cron** (D7); proof by receipt |
| `plugins.py` | `plugins/` (47) | triage D5: 35 ported / 9 surfaces / 3 abandoned |
| `lineage.py` | — | H-M1/H-M2 + 10 upstream surface pins (H-P5-1) |

`contract.json` is the public contract. `tests/` holds the adapter
suite, run by the fork's command (`pytest`).

## What the adapter is not

- It never imports the fork. `agent.py`, `models.py`, `helpers/`,
  `plugins/` are absent from the execution path (H-P5-2).
- It never reads a provider key: no `.env`, no environment read, no
  key parameter. The gateway is the only way.
- It never resurrects a cron. The job loop is the scheduler.
- It is not the UI server: `run_ui.py` stays a surface, re-pointed
  at the single daemon (D3). It is not a second daemon (H-F8-4).

## The graft was not an import (§0.2)

The three native files (`a0_egm_bridge.py`, `a0_recursive_factory.py`,
`a0_holon_swarm_runtime.py`) never import the fork — stdlib only.
They reference the sub-module by strings, paths, and a contract
(gateway `:31415` + ledger SQLite WAL). "Stop grafting" means: write
the native engine. The cut (removing the references and the gitlink)
happens at integration, by Ryan — not here.

## The 47-plugin triage (D5)

- **35 ported** — the capability lives in the native engine
  (`plugins.py`: `PORTED`, each with its native target).
- **9 surfaces** — preserved, re-pointed at the single daemon, not
  ported as code: `_telegram_integration`, `_whatsapp_integration`,
  `_email_integration`, `_kokoro_tts`, `_whisper_stt`, `_office`,
  `_oauth`, `_pin_to_top`, `_sidebar_folders`. Channel surfaces never
  have their secrets read.
- **3 abandoned** — the fork's plugin meta-system:
  `_plugin_installer`, `_plugin_scan`, `_plugin_validator`. Proof: the
  native plugin system is the adapter's own `PluginRegistry`, not the
  fork's installer/scan/validator.

`verify_triage(repo_root)` checks the triage against the gel: 47
directories, exact match (H-P5-7).

## Run the suite

From the fork root, with the pas-5 venv (pytest only, stdlib adapter):

```sh
~/workspace/.venvs-dn053/agent-zero/bin/python -m pytest aspace-agent-zero-adapter/tests -v
```

## Reserves

- **R-A1** — the fork's own suite (245 test files) is not run here:
  it requires litellm, langchain, flask, faiss-cpu and the full
  requirements stack, not installed on this VM. The adapter suite is
  the module's own suite (H-M3 scope: adapter + native tests).
- **R-A2** — H-P5-3 (durability) is CONDITIONAL on the green of pas 2
  (pi), per the design. It is recorded as such, not as PASS.
- **R-A3** — the pas-4 functions (state SQLite, context-packs, Herdr
  terminal) are a NAMED DEPENDENCY (§D8): the native port is built
  against the pas-3 base, not against them. They are named in the
  fiche, not awaited.
