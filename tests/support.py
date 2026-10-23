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
