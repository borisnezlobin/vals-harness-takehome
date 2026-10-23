from pathlib import Path

import pytest
from support import BENCHMARKS_DIR, requires_docker

from agentic_harness.benchmark import Benchmark, BenchmarkError, Grade

FIBONACCI_WRONG = "def fibonacci(n):\n    return n\n"
FIBONACCI_RIGHT = (
    "def fibonacci(n):\n"
    "    a, b = 0, 1\n"
    "    for _ in range(n):\n"
    "        a, b = b, a + b\n"
    "    return a\n"
)
TESTS_THAT_ALWAYS_PASS = "def test_ok():\n    assert True\n"


@pytest.fixture(scope="module")
def bash_operations() -> Benchmark:
    benchmark = Benchmark.load("bash-operations", BENCHMARKS_DIR)
    benchmark.build_image()
    return benchmark


@pytest.fixture(scope="module")
def python_tasks() -> Benchmark:
    benchmark = Benchmark.load("python-tasks", BENCHMARKS_DIR)
    benchmark.build_image()
    return benchmark


def prepared(benchmark: Benchmark, task_id: str, workspace: Path):
    task = benchmark.list_tasks([task_id])[0]
    benchmark.setup(task, workspace)
    return task


@requires_docker
def test_bash_task_passes_with_right_answer(bash_operations, tmp_path):
    task = prepared(bash_operations, "bash-003", tmp_path)
    (tmp_path / "count.txt").write_text("5\n")

    assert bash_operations.grade(task, tmp_path).passed


@requires_docker
def test_bash_task_fails_with_wrong_answer(bash_operations, tmp_path):
    task = prepared(bash_operations, "bash-003", tmp_path)
    (tmp_path / "count.txt").write_text("4\n")

    grade = bash_operations.grade(task, tmp_path)

    assert not grade.passed
    assert grade.details["actual"] == "4"


@requires_docker
def test_python_task_passes_with_right_solution(python_tasks, tmp_path):
    task = prepared(python_tasks, "py-002", tmp_path)
    (tmp_path / "solution.py").write_text(FIBONACCI_RIGHT)

    assert python_tasks.grade(task, tmp_path).passed


@requires_docker
def test_python_grading_restores_tampered_tests(python_tasks, tmp_path):
    task = prepared(python_tasks, "py-002", tmp_path)
    (tmp_path / "solution.py").write_text(FIBONACCI_WRONG)
    (tmp_path / "test_solution.py").write_text(TESTS_THAT_ALWAYS_PASS)

    assert not python_tasks.grade(task, tmp_path).passed


def test_grade_without_json_raises_clear_error():
    with pytest.raises(BenchmarkError, match="did not print JSON: Traceback"):
        Grade.from_report("", "Traceback (most recent call last): ...")
