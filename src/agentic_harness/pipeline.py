import subprocess
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from agentic_harness.agent import Agent
from agentic_harness.benchmark import Benchmark, BenchmarkError, Task

WORKSPACES_DIR = Path("workspaces")
AGENT_TIMEOUT_SECONDS = 600


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: str
    score: float
    duration_seconds: float
    agent_exit_code: int | None = None
    agent_timed_out: bool = False
    error: str | None = None
    details: dict = field(default_factory=dict)


def new_run_id() -> str:
    return uuid.uuid4().hex[:8]


def run_task(benchmark: Benchmark, agent: Agent, task: Task, run_dir: Path) -> TaskResult:
    started = time.monotonic()
    task_dir = run_dir / task.id
    workspace = task_dir / "workspace"
    workspace.mkdir(parents=True)
    try:
        benchmark.setup(task, workspace)
        agent_run = agent.run(
            task.prompt, benchmark.image_for(task), workspace, task_dir / "agent", AGENT_TIMEOUT_SECONDS
        )
        grade = benchmark.grade(task, workspace)
    except (BenchmarkError, subprocess.SubprocessError) as error:
        return TaskResult(task.id, "error", 0.0, time.monotonic() - started, error=str(error))
    return TaskResult(
        task.id,
        "passed" if grade.passed else "failed",
        grade.score,
        time.monotonic() - started,
        agent_exit_code=agent_run.exit_code,
        agent_timed_out=agent_run.timed_out,
        details=grade.details,
    )


def run_benchmark(
    benchmark: Benchmark, agent: Agent, tasks: list[Task], run_id: str,
    on_start: Callable[[Task], None] = lambda task: None,
    on_result: Callable[[TaskResult], None] = lambda result: None,
) -> list[TaskResult]:
    benchmark.build_image()
    run_dir = WORKSPACES_DIR / run_id
    results = []
    for task in tasks:
        on_start(task)
        result = run_task(benchmark, agent, task, run_dir)
        on_result(result)
        results.append(result)
    return results
