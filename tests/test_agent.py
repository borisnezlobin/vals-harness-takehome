import json
import subprocess
from pathlib import Path

import pytest
from support import (
    AGENT_ADAPTERS_DIR,
    BENCHMARKS_DIR,
    requires_docker,
    requires_live_model,
)

from agentic_harness import agent as agent_module
from agentic_harness.agent import Agent, AgentError
from agentic_harness.benchmark import Benchmark

RECORDS_ITS_ENVIRONMENT = """#!/bin/sh
env | grep '^HARNESS_' > "$HARNESS_OUTPUT_DIR/environment.txt"
"""

NEVER_FINISHES = """#!/bin/sh
exec sleep 600
"""

LEAVES_A_CONTAINER_RUNNING = """#!/bin/sh
echo "$HARNESS_CONTAINER_LABEL" > "$HARNESS_OUTPUT_DIR/label.txt"
docker run -d --label "$HARNESS_CONTAINER_LABEL" alpine:latest sleep 600
exec sleep 600
"""


def fake_agent(adapters_dir: Path, script: str) -> Agent:
    adapter = adapters_dir / "fake-agent"
    adapter.mkdir(parents=True)
    run_script = adapter / "run.sh"
    run_script.write_text(script)
    run_script.chmod(0o755)
    return Agent.load("agents/fake-agent", adapters_dir)


def run(agent: Agent, tmp_path: Path, timeout_seconds: int = 60):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return agent.run("Say hello", "some-image", workspace, tmp_path / "output", timeout_seconds)


def test_loads_mini_swe_agent_adapter():
    agent = Agent.load("agents/mini-swe-agent", AGENT_ADAPTERS_DIR)

    assert agent.name == "mini-swe-agent"
    assert agent.run_script.is_file()


def test_rejects_agent_without_adapter(tmp_path):
    with pytest.raises(AgentError, match="No agent adapter"):
        Agent.load("agents/unknown-agent", tmp_path)


def test_passes_task_details_to_adapter(tmp_path):
    agent = fake_agent(tmp_path / "adapters", RECORDS_ITS_ENVIRONMENT)

    result = run(agent, tmp_path)

    recorded = (tmp_path / "output" / "environment.txt").read_text()
    assert result.exit_code == 0
    assert "HARNESS_PROMPT=Say hello" in recorded
    assert "HARNESS_IMAGE=some-image" in recorded
    assert f"HARNESS_WORKSPACE={(tmp_path / 'workspace').resolve()}" in recorded


def test_stops_agent_that_runs_past_its_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_module, "SHUTDOWN_GRACE_SECONDS", 0)
    agent = fake_agent(tmp_path / "adapters", NEVER_FINISHES)

    result = run(agent, tmp_path, timeout_seconds=1)

    assert result.timed_out
    assert result.exit_code is None


@requires_docker
def test_removes_containers_left_behind_by_a_stopped_agent(tmp_path, monkeypatch):
    monkeypatch.setattr(agent_module, "SHUTDOWN_GRACE_SECONDS", 0)
    agent = fake_agent(tmp_path / "adapters", LEAVES_A_CONTAINER_RUNNING)

    run(agent, tmp_path, timeout_seconds=3)

    label = (tmp_path / "output" / "label.txt").read_text().strip()
    remaining = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"label={label}"], capture_output=True, text=True, check=False
    )
    assert remaining.stdout.strip() == ""


@requires_docker
@requires_live_model
def test_mini_swe_agent_solves_bash_001(tmp_path):
    benchmark = Benchmark.load("bash-operations", BENCHMARKS_DIR)
    benchmark.build_image()
    task = benchmark.list_tasks(["bash-001"])[0]
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    benchmark.setup(task, workspace)

    result = Agent.load("agents/mini-swe-agent", AGENT_ADAPTERS_DIR).run(
        task.prompt, benchmark.image_for(task), workspace, tmp_path / "output", timeout_seconds=300
    )

    trajectory = json.loads((tmp_path / "output" / "trajectory.json").read_text())
    assert result.exit_code == 0, result.log_path.read_text()[-2000:]
    assert trajectory["info"]["exit_status"] == "Submitted"
    assert benchmark.grade(task, workspace).passed
