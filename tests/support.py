import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"
AGENT_ADAPTERS_DIR = REPO_ROOT / "agents" / "adapters"


def docker_is_running() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0
    except FileNotFoundError:
        return False


requires_docker = pytest.mark.skipif(not docker_is_running(), reason="Docker is not running")

requires_live_model = pytest.mark.skipif(
    os.environ.get("HARNESS_LIVE_TESTS") != "1", reason="Set HARNESS_LIVE_TESTS=1 to call the real model"
)


def queue_run(store, run_id: str, task_count: int, benchmark: str = "bash-operations") -> list[str]:
    from agentic_harness.benchmark import Task

    task_ids = [f"{run_id}-task-{number}" for number in range(task_count)]
    store.create_run(run_id, "scripted-agent", benchmark, [Task(task_id, "Do the thing") for task_id in task_ids])
    return task_ids
