from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
BUILD_DIR = ROOT / ".build"
MANIFEST_PATH = BUILD_DIR / "manifest.json"
PUSH_STATE_PATH = BUILD_DIR / "push_state.json"


@dataclass(frozen=True)
class TaskRecord:
    name: str
    difficulty: str
    output: Path
    autopush: bool
    hash: str

    @property
    def task_id(self) -> str:
        return f"{self.difficulty}_{self.name}"


def error(message: str) -> None:
    print(f"[ERROR] {message}")
    raise SystemExit(1)


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.as_posix()}: JSON の形式が不正です ({exc})") from exc


def load_manifest() -> list[TaskRecord]:
    if not MANIFEST_PATH.exists():
        error(f"Manifest が存在しません: {MANIFEST_PATH.as_posix()}")

    try:
        data = load_json(MANIFEST_PATH)
    except ValueError as exc:
        error(str(exc))

    if not isinstance(data, dict):
        error("Manifest の形式が不正です: ルートは JSON オブジェクトである必要があります")

    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        error("Manifest の形式が不正です: tasks は配列である必要があります")

    records: list[TaskRecord] = []
    for index, entry in enumerate(tasks):
        if not isinstance(entry, dict):
            error(f"Manifest の形式が不正です: tasks[{index}] がオブジェクトではありません")

        name = entry.get("name")
        difficulty = entry.get("difficulty")
        output = entry.get("output")
        autopush = entry.get("autopush")
        hash_value = entry.get("hash")

        if not isinstance(name, str) or not name.strip():
            error(f"Manifest の形式が不正です: tasks[{index}].name が不正です")
        if not isinstance(difficulty, str) or not difficulty.strip():
            error(f"Manifest の形式が不正です: tasks[{index}].difficulty が不正です")
        if not isinstance(output, str) or not output.strip():
            error(f"Manifest の形式が不正です: tasks[{index}].output が不正です")
        if not isinstance(autopush, bool):
            error(f"Manifest の形式が不正です: tasks[{index}].autopush が不正です")
        if not isinstance(hash_value, str) or not hash_value.strip():
            error(f"Manifest の形式が不正です: tasks[{index}].hash が不正です")

        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = ROOT / output_path

        records.append(
            TaskRecord(
                name=name.strip(),
                difficulty=difficulty.strip(),
                output=output_path,
                autopush=autopush,
                hash=hash_value.strip(),
            )
        )

    return records


def load_push_state() -> dict[str, str]:
    if not PUSH_STATE_PATH.exists():
        return {}

    try:
        data = load_json(PUSH_STATE_PATH)
    except ValueError as exc:
        error(f"Push State の読み込み失敗: {exc}")

    if not isinstance(data, dict):
        error("Push State の読み込み失敗: ルートは JSON オブジェクトである必要があります")

    task_hashes = data.get("tasks", {})
    if not isinstance(task_hashes, dict):
        error("Push State の読み込み失敗: tasks はオブジェクトである必要があります")

    state: dict[str, str] = {}
    for key, value in task_hashes.items():
        if not isinstance(key, str) or not key.strip():
            error("Push State の読み込み失敗: tasks のキーが不正です")
        if not isinstance(value, str) or not value.strip():
            error(f"Push State の読み込み失敗: tasks[{key}] の hash が不正です")
        state[key] = value.strip()

    return state


def save_push_state(state: dict[str, str]) -> None:
    BUILD_DIR.mkdir(exist_ok=True)
    payload = {"tasks": dict(sorted(state.items()))}
    PUSH_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_command(task: TaskRecord) -> list[str]:
    output_path = task.output.relative_to(ROOT) if task.output.is_relative_to(ROOT) else task.output
    return ["kaggle", "b", "t", "push", task.task_id, "-f", output_path.as_posix()]


def format_command(task: TaskRecord) -> str:
    output_path = task.output.relative_to(ROOT) if task.output.is_relative_to(ROOT) else task.output
    return f'kaggle b t push "{task.task_id}" -f "{output_path.as_posix()}"'


def matches_difficulty(task: TaskRecord, difficulties: set[str] | None) -> bool:
    return difficulties is None or task.difficulty in difficulties


def matches_task(task: TaskRecord, task_filters: set[str] | None) -> bool:
    if task_filters is None:
        return True
    return task.name in task_filters or task.task_id in task_filters


def select_tasks(
    tasks: list[TaskRecord], difficulties: set[str] | None, task_filters: set[str] | None
) -> list[TaskRecord]:
    return [task for task in tasks if matches_difficulty(task, difficulties) and matches_task(task, task_filters)]


def validate_outputs(tasks: list[TaskRecord]) -> None:
    for task in tasks:
        if not task.output.exists():
            error(f"output が存在しません: {task.output.as_posix()}")


def push_task(task: TaskRecord) -> subprocess.CompletedProcess[str]:
    return subprocess.run(build_command(task), check=True, text=True, capture_output=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Builder が生成した manifest を使って Kaggle Benchmark へ差分 Push する"
    )
    parser.add_argument("--dry-run", action="store_true", help="Push を実行せず、実行予定のみ表示する")
    parser.add_argument("--difficulty", action="append", help="対象難易度を指定する。複数指定可")
    parser.add_argument("--task", action="append", help="対象 Task を指定する。複数指定可")
    parser.add_argument("--force", action="store_true", help="ハッシュ判定を無視してすべて Push する")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Push 失敗時も残りの Task を継続する",
    )
    return parser.parse_args()


def print_result(task: TaskRecord, status: str, detail: str | None = None) -> None:
    if detail:
        print(f"[{status}] {task.task_id} | {detail}")
    else:
        print(f"[{status}] {task.task_id}")


def run(
    tasks: list[TaskRecord], state: dict[str, str], *, dry_run: bool, force: bool, continue_on_error: bool
) -> tuple[int, int, int, int, dict[str, str]]:
    push_count = 0
    skip_count = 0
    success_count = 0
    failed_count = 0
    next_state = dict(state)

    for task in tasks:
        if not task.autopush:
            continue

        if not force and state.get(task.task_id) == task.hash:
            skip_count += 1
            print_result(task, "Skip", "Hash unchanged")
            continue

        push_count += 1
        command_text = format_command(task)

        if dry_run:
            print_result(task, "Push")
            print(f"  {command_text}")
            continue

        print_result(task, "Push", command_text)
        try:
            push_task(task)
        except FileNotFoundError:
            failed_count += 1
            print_result(task, "Failed", "Kaggle CLI が見つかりません")
            if not continue_on_error:
                break
            continue
        except subprocess.CalledProcessError as exc:
            failed_count += 1
            detail = exc.stderr.strip() if exc.stderr else exc.stdout.strip() if exc.stdout else str(exc)
            print_result(task, "Failed", detail)
            if not continue_on_error:
                break
            continue

        success_count += 1
        next_state[task.task_id] = task.hash
        save_push_state(next_state)
        print_result(task, "Success")

    return push_count, skip_count, success_count, failed_count, next_state


def main() -> None:
    args = parse_args()
    tasks = load_manifest()
    state = load_push_state()

    difficulties = set(args.difficulty) if args.difficulty else None
    task_filters = set(args.task) if args.task else None

    selected_tasks = select_tasks(tasks, difficulties, task_filters)
    validate_outputs(selected_tasks)

    push_count, skip_count, success_count, failed_count, next_state = run(
        selected_tasks,
        state,
        dry_run=args.dry_run,
        force=args.force,
        continue_on_error=args.continue_on_error,
    )

    if not args.dry_run:
        save_push_state(next_state)

    print()
    print(f"Push 数: {push_count}")
    print(f"Skip 数: {skip_count}")
    print(f"Success 数: {success_count}")
    print(f"Failed 数: {failed_count}")


if __name__ == "__main__":
    main()
