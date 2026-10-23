import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

HARNESS_LABEL = "agentic-harness"


@dataclass(frozen=True)
class Mount:
    source: Path
    target: str
    read_only: bool = False

    def as_flag(self) -> str:
        suffix = ":ro" if self.read_only else ""
        return f"{self.source.resolve()}:{self.target}{suffix}"


def run_container(
    image: str, command: list[str], mounts: list[Mount], timeout_seconds: int
) -> subprocess.CompletedProcess:
    name = f"harness-{uuid.uuid4().hex[:12]}"
    mount_flags = [flag for mount in mounts for flag in ("-v", mount.as_flag())]
    docker_command = [
        "docker", "run", "--rm", "--name", name, "--label", HARNESS_LABEL,
        "--network", "none", *mount_flags, image, *command,
    ]
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
