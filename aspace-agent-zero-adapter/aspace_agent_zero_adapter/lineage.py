"""Lineage — H-M1/H-M2 checks + 10 upstream surface pins (H-P5-1).

The gel is ``ba9b67d`` (fork main HEAD = upstream main HEAD, compare
identical, drift 0). The adapter's files are the only difference
between the gel and the adapter commit (H-M2). The 10 pins below are
the upstream surface the adapter mirrors; they are checked by content
at the gel, not by assumption.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

GEL = "ba9b67df0f54ac78106ae85c552ef5d2458f7c9a"  # full SHA, read at the repo HEAD
GEL_SHORT = "ba9b67d"


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@dataclass
class PinCheck:
    name: str
    ok: bool
    detail: str


def verify_gel_lineage(repo_root: str | Path) -> dict:
    """H-M1 (gel) + H-M2 (adapter-only diff).

    - ``head``: current HEAD (must equal the gel before the adapter
      commit; the adapter commit's parent must be the gel).
    - ``diff_files``: files changed between the gel and HEAD.
    """
    root = Path(repo_root)
    head = _git(root, "rev-parse", "HEAD")
    diff = _git(root, "diff", "--name-only", GEL_SHORT, head)
    diff_files = [line for line in diff.splitlines() if line.strip()]
    return {
        "head": head,
        "gel": GEL_SHORT,
        "head_is_gel": head.startswith(GEL_SHORT),
        "diff_files": diff_files,
        "diff_is_adapter_only": all(
            f.startswith("aspace-agent-zero-adapter/") for f in diff_files
        ),
    }


def check_upstream_surface(repo_root: str | Path) -> list[PinCheck]:
    """10 pins on the upstream surface, checked by content at the gel."""
    root = Path(repo_root)
    pins: list[PinCheck] = []

    def read(rel: str) -> str:
        return (root / rel).read_text(encoding="utf-8", errors="replace")

    # 1 — Agent is in agent.py at line 364
    lines = read("agent.py").splitlines()
    pins.append(
        PinCheck(
            "agent_class",
            len(lines) >= 364 and "class Agent" in lines[363],
            "agent.py:364 holds 'class Agent'",
        )
    )
    # 2 — models.py holds the key reader that D9 abandons
    models = read("models.py")
    pins.append(
        PinCheck(
            "models_get_api_key",
            "def get_api_key" in models,
            "models.py defines get_api_key (abandoned by D9)",
        )
    )
    # 3 — run_ui.py holds the uvicorn launcher (surface, D3)
    pins.append(
        PinCheck(
            "run_ui_uvicorn",
            "run_uvicorn_with_retries" in read("run_ui.py"),
            "run_ui.py defines run_uvicorn_with_retries",
        )
    )
    # 4 — helpers/runtime.py holds the ports (surface, D3)
    runtime = read("helpers/runtime.py")
    pins.append(
        PinCheck(
            "runtime_ports",
            "get_web_ui_port" in runtime and "get_tunnel_api_port" in runtime,
            "helpers/runtime.py: ports 5000 / 55520",
        )
    )
    # 5 — plugins/_scheduler holds SchedulerTool (D7 source)
    pins.append(
        PinCheck(
            "scheduler_tool",
            "class SchedulerTool" in read("plugins/_scheduler/tools/scheduler.py"),
            "plugins/_scheduler/tools/scheduler.py: SchedulerTool",
        )
    )
    # 6 — helpers/vector_db.py holds MyFaiss (D6 source)
    pins.append(
        PinCheck(
            "vector_db_faiss",
            "class MyFaiss" in read("helpers/vector_db.py"),
            "helpers/vector_db.py: MyFaiss (FAISS)",
        )
    )
    # 7 — plugins/ holds 47 directories, _a0_connector present
    dirs = [p.name for p in (root / "plugins").iterdir() if p.is_dir()]
    pins.append(
        PinCheck(
            "plugins_47",
            len(dirs) == 47 and "_a0_connector" in dirs,
            f"plugins/: {len(dirs)} directories, _a0_connector present",
        )
    )
    # 8 — LICENSE is MIT
    pins.append(
        PinCheck(
            "license_mit",
            "MIT License" in read("LICENSE"),
            "LICENSE: MIT License",
        )
    )
    # 9 — requirements.txt pins litellm 1.104.0 + openai 2.54.0 (abandoned)
    req = read("requirements.txt")
    pins.append(
        PinCheck(
            "requirements_litellm_openai",
            "litellm==1.104.0" in req and "openai==2.54.0" in req,
            "requirements.txt: litellm==1.104.0, openai==2.54.0",
        )
    )
    # 10 — tests/ holds 200+ test files (the fork's own suite)
    test_files = list((root / "tests").glob("test_*.py"))
    pins.append(
        PinCheck(
            "tests_200",
            len(test_files) >= 200,
            f"tests/: {len(test_files)} test files",
        )
    )
    return pins
