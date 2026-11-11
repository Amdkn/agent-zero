"""Lineage — gel, adapter-only diff, 10 surface pins (H-M1, H-M2, H-P5-1)."""

import subprocess

from aspace_agent_zero_adapter import check_upstream_surface, verify_gel_lineage

REPO_ROOT = "/home/hatch/workspace/agent-zero-repo"
GEL_FULL = "ba9b67df0f54ac78106ae85c552ef5d2458f7c9a"


def test_head_descends_from_the_gel_adapter_only():
    lineage = verify_gel_lineage(REPO_ROOT)
    if lineage["head_is_gel"]:
        # Before the adapter commit: no diff at all.
        assert lineage["diff_files"] == []
    else:
        # After the adapter commit: the diff is adapter-only, and the
        # adapter commit's parent is the gel (H-M1, H-M2).
        assert lineage["diff_is_adapter_only"] is True
        parent = subprocess.run(
            ["git", "-C", REPO_ROOT, "rev-parse", "HEAD^"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert parent == GEL_FULL


def test_ten_surface_pins_at_the_gel():
    pins = check_upstream_surface(REPO_ROOT)
    assert len(pins) == 10
    failed = [p.name for p in pins if not p.ok]
    assert failed == [], failed
    by_name = {p.name: p for p in pins}
    assert by_name["agent_class"].detail == "agent.py:364 holds 'class Agent'"
    assert by_name["plugins_47"].detail.startswith("plugins/: 47 directories")
    assert by_name["tests_200"].detail.startswith("tests/: ")
    count = int(by_name["tests_200"].detail.split(": ")[1].split(" ")[0])
    assert count >= 200
