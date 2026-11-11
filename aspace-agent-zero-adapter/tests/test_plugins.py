"""Plugins — the 47 triage, verified against the gel (H-P5-7, D5)."""

from aspace_agent_zero_adapter import (
    ABANDONED,
    PLUGIN_TRIAGE,
    PORTED,
    SURFACES,
    PluginRegistry,
    verify_triage,
)

REPO_ROOT = "/home/hatch/workspace/agent-zero-repo"


def test_triage_counts():
    assert len(PLUGIN_TRIAGE) == 47
    assert len(PORTED) == 35
    assert len(SURFACES) == 9
    assert len(ABANDONED) == 3
    assert set(PORTED) | set(SURFACES) | set(ABANDONED) == set(PLUGIN_TRIAGE)


def test_triage_against_the_gel():
    result = verify_triage(REPO_ROOT)
    assert result["count"] == 47
    assert result["missing"] == []
    assert result["extra"] == []
    assert result["ok"] is True


def test_a0_connector_is_ported():
    assert PLUGIN_TRIAGE["_a0_connector"]["verdict"] == "ported"
    assert PLUGIN_TRIAGE["_a0_connector"]["target"] == "agent_loop:egm-bridge"


def test_abandoned_are_the_meta_system_only():
    assert ABANDONED == ["_plugin_installer", "_plugin_scan", "_plugin_validator"]


def test_surfaces_are_channels_and_ui():
    assert "_telegram_integration" in SURFACES
    assert "_whatsapp_integration" in SURFACES
    assert "_email_integration" in SURFACES
    assert "_oauth" in SURFACES


def test_native_registry_registers_the_ported():
    registry = PluginRegistry()
    assert registry.register_triage() == 35
    assert len(registry) == 35
    assert registry.resolve("_scheduler") == "job_loop:JobLoop"
    assert registry.resolve("_plugin_installer") is None


def test_registry_rejects_non_prefixed_names():
    registry = PluginRegistry()
    import pytest

    with pytest.raises(ValueError):
        registry.register("plain", "somewhere")
