import fcntl
import os
import socket
import sqlite3
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

from agentic_harness.agent import Agent, AgentError
from agentic_harness.benchmark import Benchmark, BenchmarkError, Task
from agentic_harness.containers import ContainerLimits
from agentic_harness.pipeline import WORKSPACES_DIR, TaskResult, run_task
from agentic_harness.store import DATABASE_PATH, Store

THREAD_CHECK_INTERVAL_SECONDS = 0.2
RESOURCE_SHARE = 0.5
LOCK_PATH = DATABASE_PATH.with_name(f"{DATABASE_PATH.name}.lock")


@dataclass(frozen=True)
class HostResources:
    cpus: int
    memory_bytes: int

    @classmethod
    def detect(cls) -> "HostResources":
        return cls(os.cpu_count() or 1, os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))

    def worker_budget(self, limits: ContainerLimits) -> int:
        by_cpu = int(self.cpus * RESOURCE_SHARE // limits.cpus)
        by_memory = int(self.memory_bytes * RESOURCE_SHARE // limits.memory_bytes)
        return max(1, min(by_cpu, by_memory))


class QueueLock:
    def __init__(self, path: Path = LOCK_PATH):
        self.path = path
        self.file = path.open("a")

    def acquire(self) -> bool:
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        self.file.truncate(0)
        self.file.write(str(os.getpid()))
        self.file.flush()
        return True

    def release(self) -> None:
        fcntl.flock(self.file, fcntl.LOCK_UN)

    def holder_pid(self) -> int | None:
        if self.acquire():
            self.release()
            return None
        holder = self.path.read_text().strip()
        return int(holder) if holder.isdigit() else None


class WorkerPool:
    def __init__(self, size: int, limits: ContainerLimits):
        self.stopping = threading.Event()
        worker_prefix = f"{socket.gethostname().split('.')[0]}-{os.getpid()}"
        self.threads = [
            threading.Thread(
                target=work_loop,
                args=(f"{worker_prefix}-{slot}", limits, self.stopping),
            )
            for slot in range(size)
        ]

    def start(self) -> None:
        for thread in self.threads:
            thread.start()

    def is_alive(self) -> bool:
        return any(thread.is_alive() for thread in self.threads)

    def wait(self) -> None:
        while self.is_alive():
            time.sleep(THREAD_CHECK_INTERVAL_SECONDS)

    def stop(self) -> None:
        self.stopping.set()
        while self.is_alive():
            try:
                self.wait()
            except KeyboardInterrupt:
                continue


def work_loop(worker_id: str, limits: ContainerLimits, stopping: threading.Event) -> None:
    store = Store()
    while not stopping.is_set():
        claimed = store.claim_next_task(worker_id)
        if claimed is None:
            return
        result = execute_claimed_task(store, claimed, limits)
        if stopping.is_set():
            store.requeue_task(claimed["run_id"], claimed["task_id"])
            return
        store.save_task_result(claimed["run_id"], result)
        store.finish_run_if_done(claimed["run_id"])


def execute_claimed_task(store: Store, claimed: sqlite3.Row, limits: ContainerLimits) -> TaskResult:
    started = time.monotonic()
    run = store.get_run(claimed["run_id"])
    task = Task(claimed["task_id"], claimed["prompt"], claimed["image"])
    try:
        benchmark = Benchmark.load(run["benchmark"])
        agent = Agent.load(run["agent"])
        return run_task(benchmark, agent, task, WORKSPACES_DIR / run["run_id"], limits)
    except (BenchmarkError, AgentError) as error:
        return TaskResult(task.id, "error", 0.0, time.monotonic() - started, error=str(error))
    except Exception:  # noqa: BLE001 - a crash here would leave the task stuck as running
        return TaskResult(task.id, "error", 0.0, time.monotonic() - started, error=traceback.format_exc())
