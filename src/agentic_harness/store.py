import json
import sqlite3
import time
from pathlib import Path

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
    status TEXT NOT NULL,
    score REAL,
    duration_seconds REAL,
    agent_exit_code INTEGER,
    agent_timed_out INTEGER,
    error TEXT,
    details TEXT,
    PRIMARY KEY (run_id, task_id)
);
"""


class Store:
    def __init__(self, path: Path = DATABASE_PATH):
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript(SCHEMA)

    def create_run(self, run_id: str, agent: str, benchmark: str, task_ids: list[str]) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO runs VALUES (?, ?, ?, 'running', ?, NULL)", (run_id, agent, benchmark, time.time())
            )
            self.connection.executemany(
                "INSERT INTO task_results (run_id, task_id, status) VALUES (?, ?, 'queued')",
                [(run_id, task_id) for task_id in task_ids],
            )

    def mark_task_running(self, run_id: str, task_id: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE task_results SET status = 'running' WHERE run_id = ? AND task_id = ?", (run_id, task_id)
            )

    def save_task_result(self, run_id: str, result: TaskResult) -> None:
        with self.connection:
            self.connection.execute(
                """UPDATE task_results SET status = ?, score = ?, duration_seconds = ?, agent_exit_code = ?,
                   agent_timed_out = ?, error = ?, details = ? WHERE run_id = ? AND task_id = ?""",
                (result.status, result.score, result.duration_seconds, result.agent_exit_code,
                 result.agent_timed_out, result.error, json.dumps(result.details), run_id, result.task_id),
            )

    def finish_run(self, run_id: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE runs SET status = 'completed', finished_at = ? WHERE run_id = ?", (time.time(), run_id)
            )

    def get_run(self, run_id: str) -> sqlite3.Row | None:
        return self.connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()

    def get_task_results(self, run_id: str) -> list[sqlite3.Row]:
        return self.connection.execute(
            "SELECT * FROM task_results WHERE run_id = ? ORDER BY rowid", (run_id,)
        ).fetchall()
