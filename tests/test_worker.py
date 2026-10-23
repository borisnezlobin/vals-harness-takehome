import os
import threading

import pytest
from support import queue_run

from agentic_harness import worker as worker_module
from agentic_harness.containers import DEFAULT_LIMITS, ContainerLimits
from agentic_harness.pipeline import TaskResult
from agentic_harness.worker import HostResources, QueueLock, WorkerPool

GIGABYTE = 1024**3


def passes_instantly(benchmark, agent, task, run_dir, limits):
    return TaskResult(task.id, "passed", 1.0, 0.0)


@pytest.mark.parametrize(
    ("cpus", "memory_gb", "expected"),
    [(10, 16, 4), (16, 64, 8), (2, 64, 1), (1, 1, 1)],
)
def test_worker_budget_uses_half_the_scarcer_resource(cpus, memory_gb, expected):
    assert HostResources(cpus, memory_gb * GIGABYTE).worker_budget(DEFAULT_LIMITS) == expected


def test_worker_budget_follows_the_task_limits():
    small_tasks = ContainerLimits(cpus=0.5, memory_gb=1)
    assert HostResources(10, 16 * GIGABYTE).worker_budget(small_tasks) == 8


def test_only_one_queue_lock_can_be_held(tmp_path):
    first, second = QueueLock(tmp_path / "queue.lock"), QueueLock(tmp_path / "queue.lock")
    assert first.acquire()
    assert not second.acquire()
    first.release()
    assert second.acquire()


def test_queue_lock_reports_the_process_holding_it(tmp_path):
    holder, observer = QueueLock(tmp_path / "queue.lock"), QueueLock(tmp_path / "queue.lock")
    assert observer.holder_pid() is None
    assert holder.acquire()
    assert observer.holder_pid() == os.getpid()


def test_pool_runs_every_task_once_and_completes_the_runs(harness_dir, store, monkeypatch):
    seen: list[str] = []
    seen_lock = threading.Lock()

    def records_and_passes(benchmark, agent, task, run_dir, limits):
        with seen_lock:
            seen.append(task.id)
        return passes_instantly(benchmark, agent, task, run_dir, limits)

    monkeypatch.setattr(worker_module, "run_task", records_and_passes)
    expected = queue_run(store, "run-a", 5) + queue_run(store, "run-b", 3)
    pool = WorkerPool(3, DEFAULT_LIMITS)
    pool.start()
    pool.wait()
    assert sorted(seen) == sorted(expected)
    assert {store.get_run(run_id)["status"] for run_id in ("run-a", "run-b")} == {"completed"}


def test_stopping_puts_the_in_flight_task_back_in_the_queue(harness_dir, store, monkeypatch):
    started, release = threading.Event(), threading.Event()

    def waits_for_release(benchmark, agent, task, run_dir, limits):
        started.set()
        release.wait(timeout=10)
        return passes_instantly(benchmark, agent, task, run_dir, limits)

    monkeypatch.setattr(worker_module, "run_task", waits_for_release)
    queue_run(store, "run-a", 2)
    pool = WorkerPool(1, DEFAULT_LIMITS)
    pool.start()
    assert started.wait(timeout=10)
    pool.stopping.set()
    release.set()
    pool.wait()
    assert [row["status"] for row in store.get_task_results("run-a")] == ["queued", "queued"]


def test_a_crash_inside_a_task_is_recorded_as_an_error(harness_dir, store, monkeypatch):
    def crashes(benchmark, agent, task, run_dir, limits):
        raise RuntimeError("something unexpected")

    monkeypatch.setattr(worker_module, "run_task", crashes)
    queue_run(store, "run-a", 1)
    pool = WorkerPool(1, DEFAULT_LIMITS)
    pool.start()
    pool.wait()
    (row,) = store.get_task_results("run-a")
    assert row["status"] == "error"
    assert "RuntimeError: something unexpected" in row["error"]
    assert store.get_run("run-a")["status"] == "completed"


def test_an_unknown_agent_is_recorded_as_an_error(harness_dir, store):
    queue_run(store, "run-a", 1)
    store.connection.execute("UPDATE runs SET agent = 'missing-agent'")
    store.connection.commit()
    pool = WorkerPool(1, DEFAULT_LIMITS)
    pool.start()
    pool.wait()
    (row,) = store.get_task_results("run-a")
    assert row["status"] == "error"
    assert "No agent adapter found" in row["error"]
