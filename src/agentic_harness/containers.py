import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

HARNESS_LABEL = "agentic-harness"
SANDBOX_FLAGS = ("--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges")


@dataclass(frozen=True)
class Mount:
    source: Path
    target: str
    read_only: bool = False

    def as_flag(self) -> str:
        suffix = ":ro" if self.read_only else ""
        return f"{self.source.resolve()}:{self.target}{suffix}"


@dataclass(frozen=True)
class ContainerLimits:
    cpus: float = 1.0
    memory_gb: float = 2.0
    max_processes: int = 256

    @property
    def memory_bytes(self) -> int:
        return int(self.memory_gb * 1024**3)

    def as_flags(self) -> list[str]:
        return ["--cpus", str(self.cpus), "--memory", str(self.memory_bytes), "--pids-limit", str(self.max_processes)]


DEFAULT_LIMITS = ContainerLimits()


def sandbox_run_args(label: str, mounts: list[Mount], limits: ContainerLimits) -> list[str]:
    mount_flags = [flag for mount in mounts for flag in ("-v", mount.as_flag())]
    return ["--rm", "--label", label, *SANDBOX_FLAGS, *limits.as_flags(), *mount_flags]


def run_container(
    image: str, command: list[str], mounts: list[Mount], timeout_seconds: int,
    limits: ContainerLimits = DEFAULT_LIMITS,
) -> subprocess.CompletedProcess:
    name = f"harness-{uuid.uuid4().hex[:12]}"
    docker_command = ["docker", "run", "--name", name, *sandbox_run_args(HARNESS_LABEL, mounts, limits), image, *command]
    try:
        return subprocess.run(
            docker_command, capture_output=True, text=True, timeout=timeout_seconds, check=False
        )
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)
        raise


def remove_labeled_containers(label: str) -> None:
    listing = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"label={label}"], capture_output=True, text=True, check=False
    )
    container_ids = listing.stdout.split()
    if container_ids:
        subprocess.run(["docker", "rm", "-f", *container_ids], capture_output=True, check=False)
