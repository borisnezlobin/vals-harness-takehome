"""CLI for the agentic harness system."""

import subprocess
import time

import click

from agentic_harness.agent import Agent, AgentError
from agentic_harness.benchmark import Benchmark, BenchmarkError
from agentic_harness.containers import (
    HARNESS_LABEL,
    ContainerLimits,
    remove_labeled_containers,
)
from agentic_harness.pipeline import new_run_id
from agentic_harness.progress import QueueProgress
from agentic_harness.report import (
    FORMATTERS,
    build_report,
    format_run_list,
    format_status,
)
from agentic_harness.store import Store
from agentic_harness.worker import HostResources, QueueLock, WorkerPool

PROGRESS_REFRESH_SECONDS = 0.5
RECENT_RUNS_SHOWN = 5


@click.group()
def cli():
    """Agentic Harness"""


@cli.command()
@click.option(
    "--agent",
    default=None,
    help="Path to the agent directory or configuration file",
)
@click.option(
    "--benchmark",
    default=None,
    help="Name of the benchmark to run (e.g., bash-operations)",
)
@click.option(
    "--task_ids",
    default=None,
    help="Comma-separated list of task IDs to run (runs all tasks if not provided)",
)
@click.option(
    "--workers",
    type=click.IntRange(min=1),
    default=None,
    help="Number of tasks to run at once (default: as many as fit in half of this machine's CPUs and memory)",
)
@click.option(
    "--task_cpus",
    type=click.FloatRange(min=0.1),
    default=1.0,
    help="CPUs each task's containers may use (default: 1)",
)
@click.option(
    "--task_memory_gb",
    type=click.FloatRange(min=0.1),
    default=2.0,
    help="Memory each task's containers may use, in GB (default: 2)",
)
def run(
    agent: str | None, benchmark: str | None, task_ids: str | None,
    workers: int | None, task_cpus: float, task_memory_gb: float,
):
    """Add a run to the queue, then work through the queue until it's empty.

    Without --agent and --benchmark, it works through whatever is already queued.
    """
    if bool(agent) != bool(benchmark):
        raise click.UsageError("--agent and --benchmark need to be given together")
    store = Store()
    if agent and benchmark:
        queue_run(store, agent, benchmark, task_ids)
    lock = QueueLock()
    if not lock.acquire():
        click.echo("Another harness run is already working through the queue. It will get to everything queued.")
        return
    limits = ContainerLimits(cpus=task_cpus, memory_gb=task_memory_gb)
    work_through_queue(store, lock, workers, limits)


def queue_run(store: Store, agent: str, benchmark: str, task_ids: str | None) -> None:
    try:
        loaded_benchmark = Benchmark.load(benchmark)
        loaded_agent = Agent.load(agent)
        tasks = loaded_benchmark.list_tasks(task_ids.split(",") if task_ids else None)
        loaded_benchmark.build_image()
    except (BenchmarkError, AgentError) as error:
        raise click.ClickException(str(error)) from error
    except subprocess.CalledProcessError as error:
        raise click.ClickException(f"Building the {benchmark} image failed") from error
    run_id = new_run_id()
    store.create_run(run_id, loaded_agent.name, benchmark, tasks)
    click.echo(f"Queued run {run_id}: {loaded_agent.name} on {benchmark}, {pluralize(len(tasks), 'task')}")


def work_through_queue(store: Store, lock: QueueLock, workers: int | None, limits: ContainerLimits) -> None:
    requeued = store.requeue_running_tasks()
    if requeued:
        remove_labeled_containers(HARNESS_LABEL)
        click.echo(f"Put {pluralize(requeued, 'task')} from an interrupted run back in the queue.")
    if not store.has_queued_tasks():
        click.echo("Nothing is queued.")
        return
    size = workers or default_worker_count(limits)
    click.echo("Press Ctrl-C to stop. Tasks that were running go back in the queue.")
    with QueueProgress(store) as progress:
        while run_pool(WorkerPool(size, limits), progress):
            lock.release()
            if not store.has_queued_tasks() or not lock.acquire():
                return
    click.echo("Stopped. Run harness run again to pick up the tasks still in the queue.")


def run_pool(pool: WorkerPool, progress: QueueProgress) -> bool:
    pool.start()
    try:
        while pool.is_alive():
            progress.refresh()
            time.sleep(PROGRESS_REFRESH_SECONDS)
    except KeyboardInterrupt:
        progress.console.print("Stopping...")
        pool.stop()
        return False
    finally:
        progress.refresh()
    return True


def default_worker_count(limits: ContainerLimits) -> int:
    resources = HostResources.detect()
    budget = resources.worker_budget(limits)
    click.echo(
        f"Running {pluralize(budget, 'task')} at a time. That's as many as fit in half of this machine's "
        f"{resources.cpus} CPUs and {resources.memory_bytes / 1024**3:.0f} GB at "
        f"{limits.cpus:g} CPU and {limits.memory_gb:g} GB per task."
    )
    return budget


def load_report(store: Store, run_id: str) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise click.ClickException(f"No run with ID {run_id}")
    return build_report(run, store.get_task_results(run_id))


@cli.command()
@click.option(
    "--run_id",
    default=None,
    help="The unique identifier for the benchmark run (lists active runs if not provided)",
)
def status(run_id: str | None):
    """Check the status of a benchmark run, or list active runs."""
    store = Store()
    if run_id:
        click.echo(format_status(load_report(store, run_id)))
        return
    active = [load_report(store, active_id) for active_id in store.get_unfinished_run_ids()]
    recent = [load_report(store, recent_id) for recent_id in store.get_recent_finished_run_ids(RECENT_RUNS_SHOWN)]
    click.echo(format_run_list(active, recent))


@cli.command()
@click.option(
    "--run_id",
    required=True,
    help="The unique identifier for the benchmark run",
)
@click.option(
    "--format",
    type=click.Choice(["json", "table", "summary"], case_sensitive=False),
    default="json",
    help="Output format for results (default: json)",
)
def results(run_id: str, format: str):
    """Get results from a completed run."""
    click.echo(FORMATTERS[format.lower()](load_report(Store(), run_id)))


def pluralize(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
