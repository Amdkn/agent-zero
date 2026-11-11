"""Job loop — scheduler as daemon job loop, proof by receipt (H-P5-6, D7)."""

import pytest

from aspace_agent_zero_adapter import JobLoop, TaskKind


def test_create_and_run_scheduled_task_with_receipt(tmp_path):
    loop = JobLoop(tmp_path / "ledger.jsonl")
    task = loop.create_task(
        TaskKind.SCHEDULED,
        "nightly check",
        {"check": "presence"},
        run_at=1000.0,
    )
    assert task.status == "pending"
    receipts = loop.run_due(now=1000.0)
    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt["task_id"] == task.task_id
    assert receipt["name"] == "nightly check"
    assert receipt["kind"] == "scheduled"
    assert receipt["executed_at"] == 1000.0
    assert '"check": "presence"' in receipt["result"]
    assert loop.read_receipts()[0]["receipt_id"] == receipt["receipt_id"]
    assert loop.get_task(task.task_id).status == "done"


def test_adhoc_task_runs_now(tmp_path):
    loop = JobLoop(tmp_path / "ledger.jsonl")
    task = loop.create_task(TaskKind.ADHOC, "now", {"x": 1})
    receipts = loop.run_due(now=0.0)
    assert [r["task_id"] for r in receipts] == [task.task_id]


def test_future_task_does_not_run_early(tmp_path):
    loop = JobLoop(tmp_path / "ledger.jsonl")
    loop.create_task(TaskKind.PLANNED, "later", {}, run_at=5000.0)
    assert loop.run_due(now=100.0) == []


def test_cron_is_refused(tmp_path):
    loop = JobLoop(tmp_path / "ledger.jsonl")
    with pytest.raises(ValueError, match="cron is refused"):
        loop.create_task(TaskKind.SCHEDULED, "nope", {}, cron="*/30 * * * *")
    task = loop.create_task(TaskKind.SCHEDULED, "ok", {})
    with pytest.raises(ValueError, match="cron is refused"):
        loop.update_task(task.task_id, cron="0 * * * *")


def test_unknown_handler_is_refused(tmp_path):
    loop = JobLoop(tmp_path / "ledger.jsonl")
    with pytest.raises(ValueError, match="unknown handler"):
        loop.create_task(TaskKind.ADHOC, "x", {}, handler="nope")


def test_custom_handler_executes(tmp_path):
    loop = JobLoop(
        tmp_path / "ledger.jsonl",
        handlers={"double": lambda payload: str(payload["n"] * 2)},
    )
    task = loop.create_task(TaskKind.ADHOC, "d", {"n": 21}, handler="double")
    receipt = loop.run_task(task.task_id)
    assert receipt["result"] == "42"


def test_delete_and_list(tmp_path):
    loop = JobLoop(tmp_path / "ledger.jsonl")
    keep = loop.create_task(TaskKind.ADHOC, "keep", {})
    drop = loop.create_task(TaskKind.ADHOC, "drop", {})
    assert loop.delete_task(drop.task_id) is True
    assert [t.task_id for t in loop.list_tasks()] == [keep.task_id]
    assert loop.list_tasks(kind=TaskKind.SCHEDULED) == []
