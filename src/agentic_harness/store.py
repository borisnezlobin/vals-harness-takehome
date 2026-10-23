import json
import sqlite3
import time
from pathlib import Path

from agentic_harness.benchmark import Task
from agentic_harness.pipeline import TaskResult

DATABASE_PATH = Path("harness.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    benchmark TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    finished_at REAL
);
CREATE TABLE IF NOT EXISTS task_results (
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    task_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    image TEXT,
    status TEXT NOT NULL,
    worker_id TEXT,
    claimed_at REAL,
    score REAL,
    duration_seconds REAL,
    agent_exit_code INTEGER,
    agent_timed_out INTEGER,
    error TEXT,
    details TEXT,
    PRIMARY KEY (run_id, task_id)
);
"""

CLAIM_NEXT_TASK = """
UPDATE task_results SET status = 'running', worker_id = ?, claimed_at = ?
WHERE rowid = (SELECT rowid FROM task_results WHERE status = 'queued' ORDER BY rowid LIMIT 1)
RETURNING run_id, task_id, prompt, image
"""


class Store:
    def __init__(self, path: Path = DATABASE_PATH):
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript(SCHEMA)

    def create_run(self, run_id: str, agent: str, benchmark: str, tasks: list[Task]) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO runs VALUES (?, ?, ?, 'queued', ?, NULL)", (run_id, agent, benchmark, time.time())
            )
            self.connection.executemany(
                "INSERT INTO task_results (run_id, task_id, prompt, image, status) VALUES (?, ?, ?, ?, 'queued')",
                [(run_id, task.id, task.prompt, task.image) for task in tasks],
            )

    def claim_next_task(self, worker_id: str) -> sqlite3.Row | None:
        with self.connection:
            claimed = self.connection.execute(CLAIM_NEXT_TASK, (worker_id, time.time())).fetchall()
            if not claimed:
                return None
            self.connection.execute(
                "UPDATE runs SET status = 'running' WHERE run_id = ? AND status = 'queued'", (claimed[0]["run_id"],)
            )
        return claimed[0]

    def requeue_task(self, run_id: str, task_id: str) -> None:
        with self.connection:
            self.connection.execute(
                """UPDATE task_results SET status = 'queued', worker_id = NULL, claimed_at = NULL
                   WHERE run_id = ? AND task_id = ?""",
                (run_id, task_id),
            )

    def requeue_running_tasks(self) -> int:
        with self.connection:
            return self.connection.execute(
                "UPDATE task_results SET status = 'queued', worker_id = NULL, claimed_at = NULL WHERE status = 'running'"
            ).rowcount

    def has_queued_tasks(self) -> bool:
        return self.connection.execute("SELECT 1 FROM task_results WHERE status = 'queued' LIMIT 1").fetchone() is not None

    def get_unfinished_run_ids(self) -> list[str]:
        rows = self.connection.execute("SELECT run_id FROM runs WHERE status != 'completed' ORDER BY created_at")
        return [row["run_id"] for row in rows]

    def get_recent_finished_run_ids(self, limit: int) -> list[str]:
        rows = self.connection.execute(
            "SELECT run_id FROM runs WHERE status = 'completed' ORDER BY finished_at DESC LIMIT ?", (limit,)
        )
        return [row["run_id"] for row in rows]

    def save_task_result(self, run_id: str, result: TaskResult) -> None:
        with self.connection:
            self.connection.execute(
                """UPDATE task_results SET status = ?, score = ?, duration_seconds = ?, agent_exit_code = ?,
                   agent_timed_out = ?, error = ?, details = ? WHERE run_id = ? AND task_id = ?""",
                (result.status, result.score, result.duration_seconds, result.agent_exit_code,
                 result.agent_timed_out, result.error, json.dumps(result.details), run_id, result.task_id),
            )

    def finish_run_if_done(self, run_id: str) -> None:
        with self.connection:
            self.connection.execute(
                """UPDATE runs SET status = 'completed', finished_at = ?
                   WHERE run_id = ? AND status != 'completed' AND NOT EXISTS (
                       SELECT 1 FROM task_results WHERE run_id = ? AND status IN ('queued', 'running'))""",
                (time.time(), run_id, run_id),
            )

    def get_run(self, run_id: str) -> sqlite3.Row | None:
        return self.connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()

    def get_task_results(self, run_id: str) -> list[sqlite3.Row]:
        return self.connection.execute(
            "SELECT * FROM task_results WHERE run_id = ? ORDER BY rowid", (run_id,)
        ).fetchall()
