import threading

from support import queue_run

from agentic_harness.pipeline import TaskResult
from agentic_harness.store import Store


def finish(store: Store, run_id: str, task_id: str, status: str = "passed") -> None:
    store.save_task_result(run_id, TaskResult(task_id, status, 1.0 if status == "passed" else 0.0, 1.0))
    store.finish_run_if_done(run_id)


def test_new_run_queues_every_task(store):
    task_ids = queue_run(store, "run-a", 3)
    assert store.get_run("run-a")["status"] == "queued"
    assert [(row["task_id"], row["status"]) for row in store.get_task_results("run-a")] == [
        (task_id, "queued") for task_id in task_ids
    ]


def test_claim_takes_the_oldest_task_and_starts_its_run(store):
    first_ids = queue_run(store, "run-a", 2)
    queue_run(store, "run-b", 2)
    claimed = store.claim_next_task("worker-1")
    assert (claimed["run_id"], claimed["task_id"], claimed["prompt"]) == ("run-a", first_ids[0], "Do the thing")
    assert store.get_run("run-a")["status"] == "running"
    assert store.get_run("run-b")["status"] == "queued"


def test_claim_returns_nothing_when_the_queue_is_empty(store):
    queue_run(store, "run-a", 1)
    store.claim_next_task("worker-1")
    assert store.claim_next_task("worker-1") is None
    assert not store.has_queued_tasks()


def test_concurrent_claims_never_hand_out_a_task_twice(store, tmp_path):
    expected = queue_run(store, "run-a", 20) + queue_run(store, "run-b", 20)
    claimed: list[str] = []
    claimed_lock = threading.Lock()

    def claim_until_empty(worker_id: str) -> None:
        worker_store = Store(tmp_path / "harness.db")
        while (row := worker_store.claim_next_task(worker_id)) is not None:
            with claimed_lock:
                claimed.append(row["task_id"])

    threads = [threading.Thread(target=claim_until_empty, args=(f"worker-{n}",)) for n in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(claimed) == sorted(expected)


def test_run_completes_only_after_its_last_task(store):
    first, second = queue_run(store, "run-a", 2)
    store.claim_next_task("worker-1")
    finish(store, "run-a", first)
    assert store.get_run("run-a")["status"] == "running"
    store.claim_next_task("worker-1")
    finish(store, "run-a", second, status="failed")
    run = store.get_run("run-a")
    assert run["status"] == "completed"
    assert run["finished_at"] is not None


def test_stale_running_tasks_go_back_in_the_queue(store):
    queue_run(store, "run-a", 3)
    store.claim_next_task("worker-1")
    store.claim_next_task("worker-2")
    assert store.requeue_running_tasks() == 2
    statuses = [row["status"] for row in store.get_task_results("run-a")]
    assert statuses == ["queued", "queued", "queued"]
    assert store.get_task_results("run-a")[0]["worker_id"] is None


def test_unfinished_and_recently_finished_runs_are_listed(store):
    for run_id in ("run-a", "run-b", "run-c"):
        (task_id,) = queue_run(store, run_id, 1)
        if run_id != "run-c":
            store.claim_next_task("worker-1")
            finish(store, run_id, task_id)
    assert store.get_unfinished_run_ids() == ["run-c"]
    assert store.get_recent_finished_run_ids(limit=5) == ["run-b", "run-a"]
    assert store.get_recent_finished_run_ids(limit=1) == ["run-b"]
