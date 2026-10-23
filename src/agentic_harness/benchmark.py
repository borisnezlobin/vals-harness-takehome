import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

BENCHMARKS_DIR = Path("benchmarks")


class BenchmarkError(Exception):
    pass


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    image: str | None = None


@dataclass(frozen=True)
class Benchmark:
    name: str
    root: Path

    @classmethod
    def load(cls, name: str, benchmarks_dir: Path = BENCHMARKS_DIR) -> "Benchmark":
        root = (benchmarks_dir / name).resolve()
        if not (root / "harness").is_dir():
            raise BenchmarkError(f"No harness adapter found at {root / 'harness'}")
        return cls(name=name, root=root)

    @property
    def adapter_dir(self) -> Path:
        return self.root / "harness"

    @property
    def image_tag(self) -> str:
        return f"harness-{self.name}"

    def list_tasks(self, task_ids: list[str] | None = None) -> list[Task]:
        listing = subprocess.run(
            [self.adapter_dir / "tasks.sh"], capture_output=True, text=True, check=True
        )
        tasks = [Task(t["id"], t["prompt"], t.get("image")) for t in json.loads(listing.stdout)]
        if task_ids is None:
            return tasks
        return self._select(tasks, task_ids)

    def build_image(self) -> str:
        subprocess.run(
            ["docker", "build", "-q", "-f", self.adapter_dir / "Dockerfile", "-t", self.image_tag, self.root],
            capture_output=True,
            check=True,
        )
        return self.image_tag

    def image_for(self, task: Task) -> str:
        return task.image or self.image_tag

    @staticmethod
    def _select(tasks: list[Task], task_ids: list[str]) -> list[Task]:
        by_id = {task.id: task for task in tasks}
        unknown = [task_id for task_id in task_ids if task_id not in by_id]
        if unknown:
            raise BenchmarkError(f"Unknown task IDs: {', '.join(unknown)}")
        return [by_id[task_id] for task_id in task_ids]
