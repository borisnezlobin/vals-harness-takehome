# Agentic Harness Take-Home

`harness` runs an AI agent against a benchmark's tasks and reports how many it solved. Each task gets its own workspace folder and three short-lived Docker containers: one sets the task up, one is where the agent works, and one grades the result. Runs wait in a SQLite queue. `harness run` works through that queue several tasks at a time and draws a progress bar for each run.

## How it works

![Harness Explanation Diagram](image.png)

**A couple of additional notes**:
1. In reality, the "docker container" is three separate containers—this is to prevent the grading resources (scripts, answers, etc.) from being mounted inside the agent's container at any point.
2. "Write to SQLite" is more accurately "Update SQLite," since the first write actually happens right after the full list of tasks is read. (This way concurrency can work: a task runner claims a row, runs the task, and then updates that row in SQLite).
3. `harness run` actually adds the run to the queue table in SQLite rather than just running it automatically. (But once the task is at the front of the queue this diagram shows how it would look).

Not pictured:
- Run queue (`harness run` writes to the queue database; `harness` runs until the queue is empty)
- Asynchronous workers (just runs multiple tasks at once up to an automatically-calculated resource limit)
- Crash recovery (`harness` can resume benchmark runs from the database)

<hr>

## High-level overview

At a high level, the harness works by adding four adapters to every benchmark: `Dockerfile`, `grade.sh`, `setup.sh`, and `tasks.sh`. The Dockerfile specifies how each task container should be set up (a minimal, sandboxed environment per task). Then, `tasks.sh` returns the benchmark's tasks in a standard format (so the harness can write the queue into the database and work through each task). For each task, `setup.sh` sets up the workspace folder in its own container, then the container is destroyed (the workspace folder on the host machine is kept), a new one is created for the agent to work in, and when the agent is done the container is again destroyed and `grade.sh` returns a standard grade format from a third container. Mini SWE Agent runs via a .sh adapter as well (injects actions using `docker run`).

Data is stored in the SQLite database:
- queues are unclaimed database rows
- past runs are recorded in the database.

<hr>

### The queue

The queue is the `task_results` table in `harness.db`. Each task has a row. The row's `status` column says where the task is. A worker slot claims a task with one SQL statement that finds the oldest `queued` row and marks it `running` in the same step. SQLite lets only one writer in at a time. Because of that, two slots can never claim the same task.

Slots always take the oldest task. A run gets every free slot until its last task has started. After that, slots that come free move on to the next run. Two runs only overlap while the first one finishes its last few tasks.

Only one `harness run` works through the queue at a time. It holds a lock on `harness.db.lock` while it works and writes its PID into that file. The operating system drops that lock as soon as the process ends, even after a `kill -9`. When a new runner takes the lock, it knows no other runner exists. Any task still marked `running` must have been left behind by a runner that died. The new runner puts those tasks back in the queue and removes their leftover containers.

### Concurrency and resource limits

Each worker slot is a thread. Threads are enough here because a slot spends almost all its time waiting on Docker or the model's API.

The default number of slots comes from this machine's CPUs and memory. The harness takes half of each and divides by the per-task limits (1 CPU and 2 GB unless you change them). It then uses the smaller of the two answers.


### Isolation

| Container | Sees | Network | Time limit |
| --- | --- | --- | --- |
| Setup | `/workspace` (writable), `/benchmark` (read-only) | none | 5 minutes |
| Agent | `/workspace` only | none | 10 minutes, plus 30 seconds to shut down |
| Grading | `/workspace` (writable), `/benchmark` (read-only) | none | 5 minutes |

The benchmark folder holds the setup script, the grader and the expected answers. The agent's container never mounts it (which means the agent can't read the answer key—good thing to have).

Every container also drops all Linux capabilities, can't gain new privileges and can run at most 256 processes. Mini SWE Agent's loop runs on the host and calls the model from there. It only sends shell commands into the container with `docker exec`. Without `--network none`, a container could reach services on the host through `host.docker.internal`.

## Adding a benchmark

The harness only talks to a benchmark through a `harness/` folder inside it. Adding a benchmark means writing that folder, with no changes to `src/`. The benchmarks' original files stay untouched.

| File | Runs in | What it does |
| --- | --- | --- |
| `Dockerfile` | `docker build` | Builds the image (`harness-<benchmark>`) that all three containers use. Docker builds it from the benchmark folder. That lets it copy files like python-tasks' `requirements.txt`. |
| `tasks.sh` | the host | Prints a JSON list of `{"id": ..., "prompt": ...}` objects. Each dataset names these fields differently: bash-operations uses `task_id` and `problem_statement`, while python-tasks uses `id` and `prompt`. |
| `setup.sh <task_id>` | the setup container | Fills the task's empty `/workspace` with its starting files. |
| `grade.sh <task_id>` | the grading container | Prints `{"passed": ..., "score": ..., "details": ...}` as JSON. The harness reads the result from this JSON and never from exit codes, because the two benchmarks use exit codes differently. |

python-tasks' `grade.sh` runs `prepare.py` again before grading to restore the original tests. That way an agent can't pass by editing them.

## Adding an agent

An agent needs one script at `agents/adapters/<name>/run.sh`. The harness passes the task to the script in these environment variables:

| Variable | Contents |
| --- | --- |
| `HARNESS_PROMPT` | The task's prompt. |
| `HARNESS_IMAGE` | The Docker image the agent should work in. |
| `HARNESS_WORKSPACE` | The host path of the task's workspace folder. |
| `HARNESS_OUTPUT_DIR` | A folder for the agent's logs and trajectory. |
| `HARNESS_TIMEOUT_SECONDS` | How long the agent may run. |
| `HARNESS_CONTAINER_LABEL` | A label to put on any container the agent starts. The harness removes every container with this label once the agent exits. |
| `HARNESS_DOCKER_RUN_ARGS` | The full `docker run` flags for the agent's container, as a JSON list. They include the sandboxing and resource limits, the workspace mount and the label. |

Whatever the agent leaves in the workspace is what gets graded. If `run.sh` exits with 126 or 127 (the shell's codes for a command that isn't executable or wasn't found), the task counts as an `error` and isn't graded.

## Quick start

You'll need Docker running and [uv](https://docs.astral.sh/uv/) installed.

```bash
make init                  # Fetch the mini-swe-agent submodule
make install               # Install dependencies from uv.lock
source .venv/bin/activate
mini-extra config setup    # Pick a model and save its API key
harness run --agent agents/mini-swe-agent --benchmark bash-operations
```

mini-swe-agent keeps its model and API key in `.env`.

Here's what a run looks like:

```
$ harness run --agent agents/mini-swe-agent --benchmark bash-operations
Queued run 990378ad: mini-swe-agent on bash-operations, 5 tasks
Running 4 tasks at a time.
Press Ctrl-C to stop. Tasks that were running go back in the queue.
  990378ad bash-002  passed  5s
  990378ad bash-001  passed  6s
  990378ad bash-003  failed  5s
  990378ad bash-004  passed  6s
  990378ad bash-005  passed  5s
bash-operations 990378ad finished. Accuracy: 4/5 (80%), mean score 0.80
bash-operations 990378ad ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5/5 0:00:15 4 passed  0 failed  0 errors
```

## Commands

### `harness run`

```bash
harness run --agent agents/mini-swe-agent --benchmark python-tasks # run python-tasks benchmark
harness run --agent agents/mini-swe-agent --benchmark bash-operations --task_ids bash-001,bash-003 # run only specified tasks
harness run --agent agents/mini-swe-agent --benchmark bash-operations --workers 2 --task_memory_gb 1 # set custom worker resource limits
harness run --agent agents/mini-swe-agent --benchmark python-tasks --background # return automatically, run all queued benchmarks in teh background
harness run    # no options: finish whatever is already queued
```

| Option | What it does |
| --- | --- |
| `--agent` | The agent to run, as a path like `agents/mini-swe-agent`. The harness looks for its adapter at `agents/adapters/<name>/run.sh`. |
| `--benchmark` | The benchmark folder's name under `benchmarks/`. |
| `--task_ids` | A comma-separated list of tasks to run. Without it, the run includes every task. |
| `--workers` | How many tasks run at once. The default is "as many as fit in half of this machine's CPUs and memory." |
| `--task_cpus` | CPUs each task's containers may use (default 1). |
| `--task_memory_gb` | Memory each task's containers may use, in GB (default 2). |
| `--background` | Work through the queue in a separate background process and return right away. |

`harness run` builds the benchmark's Docker image, then adds one row per task to the queue. What happens next depends on whether another `harness run` is already working:

- If none is, this one works through the whole queue until it's empty. That includes runs that other terminals queue while it's going. Each run gets its own progress bar.
- If one is, this one only queues its run and exits straight away. The busy one picks the new run up and adds a bar for it.
- With `--background`, this one queues its run and starts a separate process to work through the queue. Then it exits. The background process writes its output to `workspaces/runner.log` and exits once the queue is empty. It prints its PID when it starts. `harness status` shows the PID too.
- Ctrl-C stops the runner. Tasks that were in the middle of running go back in the queue. A later `harness run` restarts them in a fresh folder.

### `harness status`

With `--run_id`, it shows one run's progress:

```
$ harness status --run_id 990378ad
Run 990378ad: running (mini-swe-agent on bash-operations)
  ██████████████████░░░░░░░░░░░░  3/5 finished: 2 passed, 1 failed, 0 errors
  Running now: bash-004, bash-005
```

Without it, it lists every run that's queued or running and says which process is working through the queue. Below those come the five runs that finished most recently:

```
$ harness status
Active runs:
  cee043f2  running  ░░░░░░░░░░░░░░░░░░░░  0/3  python-tasks (mini-swe-agent)
  04253500  queued   ░░░░░░░░░░░░░░░░░░░░  0/2  bash-operations (mini-swe-agent)
Working through the queue: PID 86178

Recently finished:
  ad77af2c  2/2 passed (100%)  bash-operations (mini-swe-agent)
  86ff4bca  3/3 passed (100%)  python-tasks (mini-swe-agent)
```

When runs are queued but no process is working through them, the PID line reads `Nothing is working through the queue. Start it with: harness run`. That usually happens if a background runner is stopped or dies.

### `harness results`

`harness results --run_id <id> --format json|table|summary` prints a run's results. JSON is the default.

```
$ harness results --run_id 1e12fec1 --format table
Task    Status  Score  Time  Error
py-001  passed  1.0    7s
py-002  passed  1.0    7s
py-003  passed  1.0    9s

$ harness results --run_id 1e12fec1 --format summary
Accuracy: 3/3 (100%), mean score 1.00
```

The JSON has the same shape for every benchmark:

```json
{
  "run_id": "1e12fec1",
  "agent": "mini-swe-agent",
  "benchmark": "python-tasks",
  "status": "completed",
  "metrics": {"total": 3, "finished": 3, "passed": 3, "failed": 0, "errors": 0, "accuracy": 1.0, "mean_score": 1.0},
  "tasks": [
    {
      "task_id": "py-001",
      "status": "passed",
      "score": 1.0,
      "duration_seconds": 7.44,
      "agent_exit_code": 0,
      "agent_timed_out": false,
      "error": null,
      "details": {"stdout": "...", "stderr": "", "return_code": 0}
    }
  ]
}
```

`accuracy` is the number of passed tasks divided by all the tasks in the run. `mean_score` averages every task's score. Both count a task that errored or hasn't finished as 0. `details` is whatever the benchmark's grader reported, unchanged.

Every task also keeps its files under `workspaces/<run_id>/<task_id>/`. The `workspace/` folder there holds what the agent left behind. The `agent/` folder holds the agent's log and, for mini-swe-agent, its full trajectory.

### Task statuses

Each task moves from `queued` to `running` and ends as one of these:

| Status | Meaning |
| --- | --- |
| `passed` | The grader ran and said the task passed. |
| `failed` | The grader ran and said it didn't. An agent that hits its time limit still gets graded. |
| `error` | The harness couldn't get a grade. Examples are a setup script that failed, an agent that never started (its `run.sh` exited with 126 or 127), a grader that printed no JSON, or setup or grading running past its time limit. |



## Testing

```bash
pytest                         # 53 tests; the Docker ones skip when Docker isn't running
HARNESS_LIVE_TESTS=1 pytest    # also runs one task against the real model
ruff check .                   # lint, including a cyclomatic complexity limit of 15
```

## Results

These numbers come from the runs we did while building the harness, with mini-swe-agent and Nemotron. The agent passed all 17 of its python-tasks attempts. On bash-operations it passed every task except bash-003. It passed bash-003 in 2 of 4 attempts.

bash-003 asks for the number of lines in `input.txt`. That file has no newline after its last line. `wc -l` counts newline characters. It reports 4 instead of 5. The agent passed whenever it noticed the mismatch and counted another way (`grep -c .`).

## Project structure

```
.
├── benchmarks/
│   ├── bash-operations/      # Bash command benchmark
│   │   ├── harness/          # Adapter the harness calls (see "Adding a benchmark")
│   │   │   ├── Dockerfile    # Image that every task container runs
│   │   │   ├── grade.sh      # Prints one task's score as JSON structured data
│   │   │   ├── setup.sh      # Fills one task's workspace with its starting files
│   │   │   └── tasks.sh      # Prints every task's ID and prompt as JSON
│   │   ├── dataset.json      # 5 bash tasks
│   │   ├── setup.py          # Setup workspace
│   │   ├── evaluate.py       # Evaluate results
│   │   └── README.md
│   └── python-tasks/         # Python coding benchmark
│       ├── harness/          # Same four files as bash-operations
│       ├── dataset.json      # 3 Python tasks
│       ├── prepare.py        # Setup workspace (different name!)
│       ├── grade.py          # Evaluate results (different name!)
│       └── README.md
├── agents/
│   ├── adapters/
│   │   └── mini-swe-agent/
│   │       └── run.sh        # Starts the agent on one task
│   └── mini-swe-agent/       # Example agent (git submodule)
├── examples/                 # The starter's scripts that run mini-swe-agent by hand
├── src/agentic_harness/
│   ├── cli.py                # The run, status and results commands
│   ├── store.py              # SQLite tables, including the queue
│   ├── worker.py             # Worker slots, the queue lock and the default slot count
│   ├── pipeline.py           # Runs one task: setup, agent, grading
│   ├── benchmark.py          # Calls a benchmark's harness/ scripts
│   ├── agent.py              # Calls an agent's run.sh
│   ├── containers.py         # docker run flags, resource limits and cleanup
│   ├── report.py             # Metrics and the text and JSON formats
│   └── progress.py           # Live progress bars
├── tests/
└── Makefile
```

## Why runs block

The Notion requires that "Users can submit multiple benchmark runs without blocking;" I think this requirement decreases the value of the `harness`. Making run submissions non-blocking would (a) not work if many benchmarks are queued (my computer would start feeling memory strain at ~4 benchmarks queued) and (b) increase the time until the first useful results are given. I chose to make benchmark runs blocking but queuable; this means:
- all CPU & RAM is put into one benchmark at a time (this means you get results faster), and
- we avoid unnecessary complexity from having to distribute workers across multiple concurrent benchmarks.

## Known limitations

- After a `kill -9`, the dead runner's agent processes keep running on the host until they hit their own step or time limit. With their containers gone, they can't change any workspace. They do keep calling the model, though. The next runner removes the containers but doesn't find those processes.
- The Docker container has no network access. More complicated evals may find this an issue.
- On a Mac, containers run inside Docker Desktop's VM. That VM may have less memory than the Mac itself. The default slot count looks at the Mac. If the VM is smaller, raise its memory in Docker Desktop's settings or pass a lower `--workers`.
- The queue lives in a local SQLite file. The lock is a local file lock too. Running workers on several machines would need a database server instead, such as Postgres with `SELECT ... FOR UPDATE SKIP LOCKED`.
- The elapsed time on a progress bar starts when that `harness run` first shows the run. It doesn't start when the run was queued.
