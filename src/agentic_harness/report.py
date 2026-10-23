import json
import sqlite3

FINISHED_STATUSES = ("passed", "failed", "error")
TABLE_HEADERS = ("Task", "Status", "Score", "Time", "Error")
ERROR_PREVIEW_LENGTH = 60


def build_report(run: sqlite3.Row, task_rows: list[sqlite3.Row]) -> dict:
    tasks = [task_entry(row) for row in task_rows]
    return {
        "run_id": run["run_id"],
        "agent": run["agent"],
        "benchmark": run["benchmark"],
        "status": run["status"],
        "metrics": compute_metrics(tasks),
        "tasks": tasks,
    }


def task_entry(row: sqlite3.Row) -> dict:
    return {
        "task_id": row["task_id"],
        "status": row["status"],
        "score": row["score"],
        "duration_seconds": row["duration_seconds"],
        "agent_exit_code": row["agent_exit_code"],
        "agent_timed_out": None if row["agent_timed_out"] is None else bool(row["agent_timed_out"]),
        "error": row["error"],
        "details": json.loads(row["details"]) if row["details"] else None,
    }


def compute_metrics(tasks: list[dict]) -> dict:
    total = len(tasks)
    counts = {status: sum(task["status"] == status for task in tasks) for status in FINISHED_STATUSES}
    total_score = sum(task["score"] or 0.0 for task in tasks)
    return {
        "total": total,
        "finished": sum(counts.values()),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "errors": counts["error"],
        "accuracy": counts["passed"] / total if total else 0.0,
        "mean_score": total_score / total if total else 0.0,
    }


def format_status(report: dict) -> str:
    metrics = report["metrics"]
    counts = f"{metrics['passed']} passed, {metrics['failed']} failed, {metrics['errors']} errors"
    lines = [
        f"Run {report['run_id']}: {report['status']} ({report['agent']} on {report['benchmark']})",
        f"  {metrics['finished']} of {metrics['total']} tasks finished: {counts}",
    ]
    running = [task["task_id"] for task in report["tasks"] if task["status"] == "running"]
    if running:
        lines.append(f"  Running now: {', '.join(running)}")
    return "\n".join(lines)


def format_summary(report: dict) -> str:
    metrics = report["metrics"]
    return (
        f"Accuracy: {metrics['passed']}/{metrics['total']} ({metrics['accuracy']:.0%}), "
        f"mean score {metrics['mean_score']:.2f}"
    )


def format_table(report: dict) -> str:
    rows = [TABLE_HEADERS, *(table_row(task) for task in report["tasks"])]
    widths = [max(len(row[column]) for row in rows) for column in range(len(TABLE_HEADERS))]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows
    )


def table_row(task: dict) -> tuple[str, ...]:
    score = "" if task["score"] is None else f"{task['score']:.1f}"
    duration = "" if task["duration_seconds"] is None else f"{task['duration_seconds']:.0f}s"
    error = task["error"].splitlines()[0][:ERROR_PREVIEW_LENGTH] if task["error"] else ""
    return (task["task_id"], task["status"], score, duration, error)


def format_json(report: dict) -> str:
    return json.dumps(report, indent=2)


FORMATTERS = {"json": format_json, "table": format_table, "summary": format_summary}
