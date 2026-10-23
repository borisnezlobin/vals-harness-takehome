from support import queue_run

from agentic_harness.pipeline import TaskResult
from agentic_harness.report import (
    build_report,
    error_preview,
    format_run_list,
    format_status,
    format_summary,
    format_table,
    progress_bar,
)


def mixed_report(store) -> dict:
    task_ids = queue_run(store, "run-a", 4)
    outcomes = [("passed", 1.0, None), ("failed", 0.5, None), ("error", 0.0, "Traceback\nOSError: disk full")]
    for task_id, (status, score, error) in zip(task_ids, outcomes):
        store.claim_next_task("worker-1")
        store.save_task_result("run-a", TaskResult(task_id, status, score, 2.0, error=error))
    store.claim_next_task("worker-1")
    return build_report(store.get_run("run-a"), store.get_task_results("run-a"))


def test_metrics_count_every_task_including_unfinished_ones(store):
    metrics = mixed_report(store)["metrics"]
    assert metrics == {
        "total": 4, "finished": 3, "passed": 1, "failed": 1, "errors": 1, "accuracy": 0.25, "mean_score": 0.375,
    }


def test_summary_and_status_text(store):
    report = mixed_report(store)
    assert format_summary(report) == "Accuracy: 1/4 (25%), mean score 0.38"
    status = format_status(report)
    assert "3/4 finished: 1 passed, 1 failed, 1 errors" in status
    assert "Running now: run-a-task-3" in status


def test_table_shows_the_end_of_the_last_error_line(store):
    table = format_table(mixed_report(store))
    assert "OSError: disk full" in table
    assert "Traceback" not in table


def test_long_errors_keep_their_ending():
    preview = error_preview("x" * 100 + " mini: not found")
    assert preview.endswith("mini: not found")
    assert preview.startswith("…")
    assert error_preview(None) == ""


def test_progress_bar_fills_in_proportion():
    assert progress_bar(1, 4, width=8) == "██░░░░░░"
    assert progress_bar(0, 0, width=4) == "████"


def test_run_list_says_when_nothing_is_active(store):
    assert format_run_list([], [], runner_pid=None) == "No runs are queued or running."
    listing = format_run_list([mixed_report(store)], [], runner_pid=4242)
    assert listing.startswith("Active runs:")
    assert "run-a  running" in listing
    assert "Working through the queue: PID 4242" in listing


def test_run_list_warns_when_queued_runs_have_no_runner(store):
    listing = format_run_list([mixed_report(store)], [], runner_pid=None)
    assert "Nothing is working through the queue. Start it with: harness run" in listing
