from typing import Self

from rich.markup import escape
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from agentic_harness.report import FINISHED_STATUSES, build_report, format_summary
from agentic_harness.store import Store

STATUS_STYLES = {"passed": "green", "failed": "red", "error": "yellow"}


class QueueProgress:
    def __init__(self, store: Store):
        self.store = store
        self.progress = Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TextColumn("{task.fields[counts]}"),
        )
        self.console = self.progress.console
        self.bars: dict[str, TaskID] = {}
        self.finished_runs: set[str] = set()
        self.reported_tasks: set[tuple[str, str]] = set()

    def __enter__(self) -> Self:
        self.progress.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self.refresh()
        self.progress.stop()

    def refresh(self) -> None:
        for run_id in dict.fromkeys([*self.bars, *self.store.get_unfinished_run_ids()]):
            if run_id not in self.finished_runs:
                self._update_run(build_report(self.store.get_run(run_id), self.store.get_task_results(run_id)))

    def _update_run(self, report: dict) -> None:
        run_id = report["run_id"]
        metrics = report["metrics"]
        if run_id not in self.bars:
            label = f"{escape(report['benchmark'])} [dim]{run_id}[/]"
            self.bars[run_id] = self.progress.add_task(label, total=metrics["total"], counts="")
        self._print_finished_tasks(report)
        self.progress.update(
            self.bars[run_id], completed=metrics["finished"], total=metrics["total"], counts=counts_markup(report)
        )
        if report["status"] == "completed":
            self.finished_runs.add(run_id)
            self.console.print(f"[bold]{escape(report['benchmark'])} {run_id}[/] finished. {format_summary(report)}")

    def _print_finished_tasks(self, report: dict) -> None:
        for task in report["tasks"]:
            key = (report["run_id"], task["task_id"])
            if task["status"] in FINISHED_STATUSES and key not in self.reported_tasks:
                self.reported_tasks.add(key)
                self.console.print(task_line(report["run_id"], task))


def task_line(run_id: str, task: dict) -> str:
    style = STATUS_STYLES[task["status"]]
    duration = f"{task['duration_seconds']:.0f}s"
    return f"  [dim]{run_id}[/] {escape(task['task_id'])}  [{style}]{task['status']}[/]  {duration}"


def counts_markup(report: dict) -> str:
    metrics = report["metrics"]
    parts = [
        f"[green]{metrics['passed']} passed[/]",
        f"[red]{metrics['failed']} failed[/]",
        f"[yellow]{metrics['errors']} errors[/]",
    ]
    running = sum(task["status"] == "running" for task in report["tasks"])
    if running:
        parts.append(f"{running} running")
    return "  ".join(parts)
