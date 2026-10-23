import json
import os
import re
import time

import pytest
from click.testing import CliRunner
from support import queue_run, requires_docker

from agentic_harness import cli as cli_module
from agentic_harness import worker as worker_module
from agentic_harness.benchmark import Benchmark
from agentic_harness.cli import cli
from agentic_harness.pipeline import TaskResult
from agentic_harness.worker import QueueLock


def child_is_running(pid: int) -> bool:
    finished_pid, _ = os.waitpid(pid, os.WNOHANG)
    return finished_pid == 0


def invoke(*args: str):
    return CliRunner().invoke(cli, list(args))


@pytest.fixture
def instant_tasks(monkeypatch):
    monkeypatch.setattr(
        worker_module, "run_task", lambda benchmark, agent, task, run_dir, limits: TaskResult(task.id, "passed", 1.0, 0.0)
    )
    monkeypatch.setattr(Benchmark, "build_image", lambda self: self.image_tag)


def test_status_lists_nothing_when_no_runs_exist(harness_dir):
    result = invoke("status")
    assert result.exit_code == 0
    assert "No runs are queued or running." in result.output


def test_status_and_results_reject_an_unknown_run(harness_dir):
    for command in ("status", "results"):
        result = invoke(command, "--run_id", "nope")
        assert result.exit_code != 0
        assert "No run with ID nope" in result.output


def test_run_needs_agent_and_benchmark_together(harness_dir):
    result = invoke("run", "--agent", "agents/scripted-agent")
    assert result.exit_code != 0
    assert "--agent and --benchmark need to be given together" in result.output


def test_run_rejects_unknown_task_ids(harness_dir, instant_tasks):
    result = invoke("run", "--agent", "agents/scripted-agent", "--benchmark", "bash-operations", "--task_ids", "nope")
    assert result.exit_code != 0
    assert "Unknown task IDs: nope" in result.output


def test_run_works_through_the_queue_and_results_report_it(harness_dir, instant_tasks, store):
    queue_run(store, "older", 2)
    result = invoke("run", "--agent", "agents/scripted-agent", "--benchmark", "bash-operations", "--workers", "2")
    assert result.exit_code == 0, result.output
    assert "older finished. Accuracy: 2/2 (100%)" in result.output
    run_ids = store.get_recent_finished_run_ids(limit=5)
    assert len(run_ids) == 2
    (new_run_id,) = set(run_ids) - {"older"}
    report = json.loads(invoke("results", "--run_id", new_run_id).output)
    assert report["metrics"]["total"] == 5
    assert report["status"] == "completed"


def test_run_only_queues_while_another_run_holds_the_lock(harness_dir, instant_tasks, store):
    holder = QueueLock()
    assert holder.acquire()
    result = invoke("run", "--agent", "agents/scripted-agent", "--benchmark", "bash-operations")
    assert result.exit_code == 0
    assert "Another harness run is already working through the queue" in result.output
    (run_id,) = store.get_unfinished_run_ids()
    assert store.get_run(run_id)["status"] == "queued"


def test_bare_run_recovers_tasks_from_a_crashed_runner(harness_dir, instant_tasks, store, monkeypatch):
    removed_labels: list[str] = []
    monkeypatch.setattr(cli_module, "remove_labeled_containers", removed_labels.append)
    queue_run(store, "crashed", 2)
    store.claim_next_task("dead-worker")
    result = invoke("run", "--workers", "1")
    assert result.exit_code == 0, result.output
    assert "Put 1 task from an interrupted run back in the queue." in result.output
    assert removed_labels == ["agentic-harness"]
    assert store.get_run("crashed")["status"] == "completed"


def test_bare_run_with_an_empty_queue(harness_dir):
    result = invoke("run")
    assert result.exit_code == 0
    assert "Nothing is queued." in result.output


@requires_docker
def test_run_end_to_end_with_a_scripted_agent(harness_dir, store):
    result = invoke(
        "run", "--agent", "agents/scripted-agent", "--benchmark", "bash-operations",
        "--task_ids", "bash-001,bash-002", "--workers", "2",
    )
    assert result.exit_code == 0, result.output
    (run_id,) = store.get_recent_finished_run_ids(limit=1)
    statuses = {row["task_id"]: row["status"] for row in store.get_task_results(run_id)}
    assert statuses == {"bash-001": "passed", "bash-002": "failed"}


def test_status_shows_which_process_works_the_queue(harness_dir, store):
    queue_run(store, "waiting", 1)
    assert "Nothing is working through the queue" in invoke("status").output
    holder = QueueLock()
    assert holder.acquire()
    assert "Working through the queue: PID" in invoke("status").output


@requires_docker
def test_background_run_returns_right_away_and_finishes_in_another_process(harness_dir, store):
    result = invoke(
        "run", "--agent", "agents/scripted-agent", "--benchmark", "bash-operations",
        "--task_ids", "bash-001", "--workers", "1", "--background",
    )
    assert result.exit_code == 0, result.output
    assert "Working through the queue in the background" in result.output
    runner_pid = int(re.search(r"PID (\d+)", result.output).group(1))
    deadline = time.monotonic() + 120
    while child_is_running(runner_pid):
        assert time.monotonic() < deadline, "the background runner never finished"
        time.sleep(0.5)
    (run_id,) = store.get_recent_finished_run_ids(limit=1)
    assert [row["status"] for row in store.get_task_results(run_id)] == ["passed"]
    assert "finished. Accuracy: 1/1 (100%)" in (harness_dir / "workspaces" / "runner.log").read_text()
