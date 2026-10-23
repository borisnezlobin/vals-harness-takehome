import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from agentic_harness.containers import HARNESS_LABEL, remove_labeled_containers

ADAPTERS_DIR = Path("agents/adapters")
SHUTDOWN_GRACE_SECONDS = 30


class AgentError(Exception):
    pass


@dataclass(frozen=True)
class AgentRun:
    exit_code: int | None
    timed_out: bool
    log_path: Path


@dataclass(frozen=True)
class Agent:
    name: str
    run_script: Path

    @classmethod
    def load(cls, agent_path: str, adapters_dir: Path = ADAPTERS_DIR) -> "Agent":
        name = Path(agent_path).name
        run_script = adapters_dir / name / "run.sh"
        if not run_script.is_file():
            raise AgentError(f"No agent adapter found at {run_script}")
        return cls(name=name, run_script=run_script.resolve())

    def run(self, prompt: str, image: str, workspace: Path, output_dir: Path, timeout_seconds: int) -> AgentRun:
        output_dir.mkdir(parents=True, exist_ok=True)
        container_label = f"{HARNESS_LABEL}={uuid.uuid4().hex[:12]}"
        environment = {
            **os.environ,
            "HARNESS_PROMPT": prompt,
            "HARNESS_IMAGE": image,
            "HARNESS_WORKSPACE": str(workspace.resolve()),
            "HARNESS_OUTPUT_DIR": str(output_dir.resolve()),
            "HARNESS_TIMEOUT_SECONDS": str(timeout_seconds),
            "HARNESS_CONTAINER_LABEL": container_label,
        }
        log_path = output_dir / "agent.log"
        try:
            return self._run_script(environment, log_path, timeout_seconds + SHUTDOWN_GRACE_SECONDS)
        finally:
            remove_labeled_containers(container_label)

    def _run_script(self, environment: dict, log_path: Path, timeout_seconds: int) -> AgentRun:
        with log_path.open("w") as log:
            try:
                completed = subprocess.run(
                    [self.run_script], env=environment, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, timeout=timeout_seconds, check=False,
                )
            except subprocess.TimeoutExpired:
                return AgentRun(exit_code=None, timed_out=True, log_path=log_path)
        return AgentRun(exit_code=completed.returncode, timed_out=False, log_path=log_path)
