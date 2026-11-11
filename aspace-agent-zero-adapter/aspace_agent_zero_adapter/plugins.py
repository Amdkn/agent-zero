"""The 47-plugin triage — design D5, written before execution.

The triage is the design's list, applied here, not discovered here:
35 ported / 9 surfaces / 3 abandoned. The count is verified against
the gel before the triage is applied (``verify_triage``): 47 plugin
directories under ``plugins/``, including ``_a0_connector`` (deduced
from the 8 ``test_a0_connector_*`` files).

- ported   — the capability lives in the native engine (named target).
- surface  — preserved, re-pointed at the single daemon, not ported
             as code. Channel surfaces never have their secrets read.
- abandoned — the fork's plugin meta-system. Proof: the native plugin
             system is the adapter's own ``PluginRegistry`` below,
             not the fork's installer/scan/validator.
"""

from __future__ import annotations

from pathlib import Path

# name -> (verdict, native target / surface, hold-out)
_TRIAGE_RAW: tuple[tuple[str, str, str], ...] = (
    # --- ported (35): the engine's capabilities, in the native engine ---
    ("_scheduler", "ported", "job_loop:JobLoop"),
    ("_memory", "ported", "memory:SharedBrainMemory+FaissIndex"),
    ("_code_execution", "ported", "agent_loop:tools/code_execution"),
    ("_browser", "ported", "agent_loop:tools/browser"),
    ("_desktop", "ported", "agent_loop:tools/desktop"),
    ("_orchestrator", "ported", "agent_loop:workers (bounded: engine workers, not a parallel rig)"),
    ("_a0_acp", "ported", "agent_loop:protocols/acp"),
    ("_a2a_chat", "ported", "agent_loop:protocols/a2a"),
    ("_a0_connector", "ported", "agent_loop:egm-bridge"),
    ("_context_window", "ported", "agent_loop:context/window"),
    ("_context_doctor", "ported", "agent_loop:context/doctor"),
    ("_error_retry", "ported", "agent_loop:retry"),
    ("_commands", "ported", "agent_loop:commands"),
    ("_goal", "ported", "agent_loop:goal"),
    ("_search_engine", "ported", "agent_loop:tools/search"),
    ("_document_query", "ported", "agent_loop:tools/document_query"),
    ("_editor", "ported", "agent_loop:tools/editor"),
    ("_text_editor", "ported", "agent_loop:tools/text_editor"),
    ("_chat_compaction", "ported", "agent_loop:chats/compaction"),
    ("_chat_branching", "ported", "agent_loop:chats/branching"),
    ("_chat_naming", "ported", "agent_loop:chats/naming"),
    ("_behavior_adjustment", "ported", "agent_loop:behavior"),
    ("_model_config", "ported", "providers:GatewayProvider"),
    ("_notify_user", "ported", "agent_loop:notify"),
    ("_wait", "ported", "job_loop:wait"),
    ("_skills", "ported", "agent_loop:skills"),
    ("_migrate_agents", "ported", "agent_loop:migrate"),
    ("_discovery", "ported", "agent_loop:discovery"),
    ("_time_travel", "ported", "agent_loop:time_travel"),
    ("_infection_check", "ported", "agent_loop:security/infection_check"),
    ("_agent_editor", "ported", "agent_loop:agent_editor"),
    ("_promptinclude", "ported", "agent_loop:security/promptinclude"),
    ("_tool_access", "ported", "agent_loop:security/tool_access"),
    ("_onboarding", "ported", "agent_loop:onboarding"),
    ("_whats_new", "ported", "agent_loop:whats_new"),
    # --- surfaces (9): preserved, re-pointed, not ported as code ---
    ("_telegram_integration", "surface", "channel:telegram (secrets never read)"),
    ("_whatsapp_integration", "surface", "channel:whatsapp (secrets never read)"),
    ("_email_integration", "surface", "channel:email (secrets never read)"),
    ("_kokoro_tts", "surface", "surface:tts"),
    ("_whisper_stt", "surface", "surface:stt"),
    ("_office", "surface", "surface:office"),
    ("_oauth", "surface", "surface:oauth (secrets never read)"),
    ("_pin_to_top", "surface", "surface:ui/pin"),
    ("_sidebar_folders", "surface", "surface:ui/folders"),
    # --- abandoned (3): the fork's plugin meta-system, with proof ---
    ("_plugin_installer", "abandoned", "meta-system: native plugin system is PluginRegistry"),
    ("_plugin_scan", "abandoned", "meta-system: native plugin system is PluginRegistry"),
    ("_plugin_validator", "abandoned", "meta-system: native plugin system is PluginRegistry"),
)

PLUGIN_TRIAGE: dict[str, dict] = {
    name: {"verdict": verdict, "target": target, "holdout": "H-P5-7"}
    for name, verdict, target in _TRIAGE_RAW
}

PORTED = sorted(n for n, v in PLUGIN_TRIAGE.items() if v["verdict"] == "ported")
SURFACES = sorted(n for n, v in PLUGIN_TRIAGE.items() if v["verdict"] == "surface")
ABANDONED = sorted(n for n, v in PLUGIN_TRIAGE.items() if v["verdict"] == "abandoned")


def verify_triage(repo_root: str | Path) -> dict:
    """Verify the triage against the gel (H-P5-7).

    Reads ``plugins/`` at the gel and compares the directory set with
    the triaged names. Returns {"ok", "count", "missing", "extra"}.
    """
    plugins_dir = Path(repo_root) / "plugins"
    on_disk = sorted(
        p.name for p in plugins_dir.iterdir() if p.is_dir() and p.name.startswith("_")
    )
    triaged = sorted(PLUGIN_TRIAGE)
    return {
        "ok": on_disk == triaged,
        "count": len(on_disk),
        "missing": [n for n in triaged if n not in on_disk],
        "extra": [n for n in on_disk if n not in triaged],
    }


class PluginRegistry:
    """The native plugin system (proof for the abandoned meta-system).

    The fork's installer/scan/validator are abandoned because the
    native engine keeps its own registry: capabilities register by
    name with a target module, and resolve to it. No installation,
    scanning, or validation of third-party plugins happens here.
    """

    def __init__(self):
        self._capabilities: dict[str, str] = {}

    def register(self, name: str, target: str) -> None:
        if not name.startswith("_"):
            raise ValueError("native plugin names start with '_' (upstream contract)")
        self._capabilities[name] = target

    def resolve(self, name: str) -> str | None:
        return self._capabilities.get(name)

    def register_triage(self) -> int:
        """Register every ported plugin from the triage. Returns count."""
        for name in PORTED:
            self.register(name, PLUGIN_TRIAGE[name]["target"])
        return len(PORTED)

    def __len__(self) -> int:
        return len(self._capabilities)
