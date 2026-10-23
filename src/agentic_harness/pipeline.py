import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from agentic_harness.agent import Agent, AgentError
from agentic_harness.benchmark import Benchmark, BenchmarkError, Task
from agentic_harness.containers import DEFAULT_LIMITS, ContainerLimits

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


def run_task(
    benchmark: Benchmark, agent: Agent, task: Task, run_dir: Path, limits: ContainerLimits = DEFAULT_LIMITS
) -> TaskResult:
    started = time.monotonic()
    task_dir = run_dir / task.id
    workspace = task_dir / "workspace"
    shutil.rmtree(task_dir, ignore_errors=True)
    workspace.mkdir(parents=True)
    try:
        benchmark.setup(task, workspace, limits)
        agent_run = agent.run(
            task.prompt, benchmark.image_for(task), workspace, task_dir / "agent", AGENT_TIMEOUT_SECONDS, limits
        )
        grade = benchmark.grade(task, workspace, limits)
    except (BenchmarkError, AgentError, subprocess.SubprocessError) as error:
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

