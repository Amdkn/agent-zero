"""Job loop — the scheduler as the daemon job loop (D7).

Upstream (gel): ``plugins/_scheduler`` is a cron inside the engine
(``crontab==1.0.1`` in requirements.txt, scheduled / adhoc / planned
tasks via ``SchedulerTool``; the engine job loop starts in
``initialize.initialize_job_loop`` -> ``helpers/job_loop.run_loop``).

Native rule (D7): the scheduler BECOMES the job loop of the single
daemon. The ``crontab`` dependency is abandoned — the job loop IS the
scheduler, not a cron. Proof (H-P5-6): a scheduled task executes and
proves itself by receipt (the execution is recorded in the ledger).
No cron is ever resurrected under another name (F8 D8, H-F8-5).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class TaskKind(str, Enum):
    SCHEDULED = "scheduled"
    ADHOC = "adhoc"
    PLANNED = "planned"


@dataclass
class Task:
    task_id: str
    kind: TaskKind
    name: str
    payload: dict
    run_at: float | None = None  # epoch seconds; None = run now (adhoc)
    handler: str = "echo"
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending | done | deleted

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "kind": self.kind.value,
            "name": self.name,
            "payload": self.payload,
            "run_at": self.run_at,
            "handler": self.handler,
            "created_at": self.created_at,
            "status": self.status,
        }


class JobLoop:
    """The daemon job loop. Tasks execute; executions prove by receipt.

    ``handlers`` maps handler names to callables ``(payload) -> str``.
    The default ``echo`` handler returns the payload as JSON. No cron
    syntax is accepted anywhere: ``create_task`` rejects any ``cron``
    argument outright.
    """

    def __init__(self, ledger_path: str | Path, handlers: dict | None = None):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self.ledger_path.touch()
        self.handlers: dict[str, object] = {"echo": self._echo_handler}
        if handlers:
            self.handlers.update(handlers)
        self._tasks: dict[str, Task] = {}

    @staticmethod
    def _echo_handler(payload: dict) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def create_task(
        self,
        kind: TaskKind | str,
        name: str,
        payload: dict | None = None,
        run_at: float | None = None,
        handler: str = "echo",
        **kwargs,
    ) -> Task:
        if "cron" in kwargs:
            raise ValueError(
                "cron is refused: the job loop is the scheduler, not a cron (D7)"
            )
        if handler not in self.handlers:
            raise ValueError(f"unknown handler {handler!r}")
        task = Task(
            task_id=str(uuid.uuid4()),
            kind=TaskKind(kind),
            name=name,
            payload=payload or {},
            run_at=run_at,
            handler=handler,
        )
        self._tasks[task.task_id] = task
        return task

    def list_tasks(self, kind: TaskKind | str | None = None) -> list[Task]:
        tasks = [t for t in self._tasks.values() if t.status != "deleted"]
        if kind is not None:
            tasks = [t for t in tasks if t.kind == TaskKind(kind)]
        return sorted(tasks, key=lambda t: t.created_at)

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def delete_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.status = "deleted"
        return True

    def update_task(self, task_id: str, **changes) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if "cron" in changes:
            raise ValueError("cron is refused (D7)")
        for key, value in changes.items():
            if hasattr(task, key):
                setattr(task, key, value)
        return task

    def run_task(self, task_id: str, clock=None) -> dict:
        """Execute one task and write its receipt to the ledger (H-P5-6)."""
        now = (clock or time.time)()
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"unknown task {task_id!r}")
        if task.status == "deleted":
            raise ValueError(f"task {task_id!r} is deleted")
        handler = self.handlers[task.handler]
        assert callable(handler)
        result = handler(task.payload)
        task.status = "done"
        receipt = {
            "receipt_id": str(uuid.uuid4()),
            "task_id": task.task_id,
            "name": task.name,
            "kind": task.kind.value,
            "handler": task.handler,
            "executed_at": now,
            "result": result,
        }
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(receipt, ensure_ascii=False) + "\n")
        return receipt

    def run_due(self, now: float | None = None) -> list[dict]:
        """Execute every pending task whose run_at has passed (adhoc: now)."""
        moment = time.time() if now is None else now
        receipts = []
        for task in self.list_tasks():
            if task.status != "pending":
                continue
            if task.run_at is None or task.run_at <= moment:
                receipts.append(self.run_task(task.task_id, clock=lambda: moment))
        return receipts

    def read_receipts(self) -> list[dict]:
        receipts: list[dict] = []
        with self.ledger_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    receipts.append(json.loads(line))
        return receipts
