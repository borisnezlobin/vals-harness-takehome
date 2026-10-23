import pytest
from support import BENCHMARKS_DIR

from agentic_harness.benchmark import Benchmark, BenchmarkError


def load(name: str) -> Benchmark:
    return Benchmark.load(name, BENCHMARKS_DIR)


def test_lists_every_bash_operations_task():
    tasks = load("bash-operations").list_tasks()

    assert [task.id for task in tasks] == ["bash-001", "bash-002", "bash-003", "bash-004", "bash-005"]
    assert tasks[0].prompt == "Create a file named 'hello.txt' containing the text 'Hello World'"


def test_python_tasks_prompts_name_the_solution_file():
    tasks = load("python-tasks").list_tasks()

    assert [task.id for task in tasks] == ["py-001", "py-002", "py-003"]
    assert all(task.prompt.endswith("Write your solution in solution.py.") for task in tasks)


def test_selects_requested_tasks_in_requested_order():
    tasks = load("bash-operations").list_tasks(["bash-003", "bash-001"])

    assert [task.id for task in tasks] == ["bash-003", "bash-001"]


def test_rejects_unknown_task_ids():
    with pytest.raises(BenchmarkError, match="bash-999"):
        load("bash-operations").list_tasks(["bash-001", "bash-999"])


def test_rejects_benchmark_without_adapter(tmp_path):
    (tmp_path / "no-adapter").mkdir()

    with pytest.raises(BenchmarkError, match="No harness adapter"):
        Benchmark.load("no-adapter", tmp_path)


def test_tasks_without_their_own_image_use_the_benchmark_image():
    benchmark = load("bash-operations")
    task = benchmark.list_tasks(["bash-001"])[0]

    assert benchmark.image_for(task) == "harness-bash-operations"
