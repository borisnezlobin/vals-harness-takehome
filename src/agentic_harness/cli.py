"""CLI for the agentic harness system."""

import click

from agentic_harness.agent import Agent, AgentError
from agentic_harness.benchmark import Benchmark, BenchmarkError, Task
from agentic_harness.pipeline import TaskResult, new_run_id, run_benchmark
from agentic_harness.report import (
    FORMATTERS,
    build_report,
    format_status,
    format_summary,
)
from agentic_harness.store import Store

STATUS_COLORS = {"passed": "green", "failed": "red", "error": "yellow"}


@click.group()
def cli():
    """Agentic Harness"""


@cli.command()
@click.option(
    "--agent",
    required=True,
    help="Path to the agent directory or configuration file",
)
@click.option(
    "--benchmark",
    required=True,
    help="Name of the benchmark to run (e.g., bash-operations)",
)
@click.option(
    "--task_ids",
    default=None,
    help="Comma-separated list of task IDs to run (runs all tasks if not provided)",
)
def run(agent: str, benchmark: str, task_ids: str | None):
    """Run an agent against a benchmark."""
    try:
        loaded_benchmark = Benchmark.load(benchmark)
        loaded_agent = Agent.load(agent)
        tasks = loaded_benchmark.list_tasks(task_ids.split(",") if task_ids else None)
    except (BenchmarkError, AgentError) as error:
        raise click.ClickException(str(error)) from error

    store = Store()
    run_id = new_run_id()
    store.create_run(run_id, loaded_agent.name, benchmark, [task.id for task in tasks])
    click.echo(f"Run {run_id}: {loaded_agent.name} on {benchmark}, {len(tasks)} tasks")

    def record_start(task: Task) -> None:
        store.mark_task_running(run_id, task.id)

    def record_result(result: TaskResult) -> None:
        store.save_task_result(run_id, result)
        echo_task_result(result)

    run_benchmark(loaded_benchmark, loaded_agent, tasks, run_id, on_start=record_start, on_result=record_result)
    store.finish_run(run_id)
    click.echo(format_summary(load_report(store, run_id)))


def echo_task_result(result: TaskResult) -> None:
    status = click.style(result.status, fg=STATUS_COLORS[result.status])
    click.echo(f"  {result.task_id}  {status}  {result.duration_seconds:.0f}s")


def load_report(store: Store, run_id: str) -> dict:
    run = store.get_run(run_id)
    if run is None:
        raise click.ClickException(f"No run with ID {run_id}")
    return build_report(run, store.get_task_results(run_id))


@cli.command()
@click.option(
    "--run_id",
    required=True,
    help="The unique identifier for the benchmark run",
)
def status(run_id: str):
    """Check the status of a benchmark run."""
    click.echo(format_status(load_report(Store(), run_id)))


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


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
