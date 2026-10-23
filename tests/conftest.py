from pathlib import Path

import pytest
from support import REPO_ROOT

from agentic_harness.store import Store

WRITES_THE_BASH_001_ANSWER = """#!/bin/sh
printf 'Hello World' > "$HARNESS_WORKSPACE/hello.txt"
"""


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "harness.db")


@pytest.fixture
def harness_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "benchmarks").symlink_to(REPO_ROOT / "benchmarks")
    adapter = tmp_path / "agents" / "adapters" / "scripted-agent"
    adapter.mkdir(parents=True)
    run_script = adapter / "run.sh"
    run_script.write_text(WRITES_THE_BASH_001_ANSWER)
    run_script.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    return tmp_path
