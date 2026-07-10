from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
TASK_DIR = ROOT / "tasks"
OUTPUT_DIR = ROOT / "generated"
BUILD_DIR = ROOT / ".build"

OUTPUT_DIR.mkdir(exist_ok=True)
BUILD_DIR.mkdir(exist_ok=True)

DIFFICULTY_NUMBERS = {
    "E": 1,
    "M": 2,
    "H": 3,
    "INS": 4,
    "INS+": 5,
}

INVALID_TASK_NAME_PREFIXES = tuple(f"{difficulty}_" for difficulty in DIFFICULTY_NUMBERS)

COMMON_IMPORTS = """import math
import re

import kaggle_benchmarks as kbench
"""

COMMON_FUNCTIONS_TEMPLATE = r"""
def normalize_choice(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    if not text:
        return ""
    token = text.split()[0]
    return token.strip(").,:;\"'")

def calculate_score(pass_count: int, loops: int) -> float:
    method = {method!r}
    if method == "log":
        if loops == 0:
            return 0.0
        score = math.log(pass_count + 1) / math.log(loops + 1)
    elif method == "squared":
        if loops == 0:
            return 0.0
        score = (pass_count / loops) ** 2
    elif method == "linear":
        if loops == 0:
            return 0.0
        score = pass_count / loops
    else:
        alpha = {alpha}
        beta = {beta}
        gamma = {gamma}
        k = {k}

        miss = loops - pass_count
        if miss == 0:
            return 1.0

        p = (pass_count + alpha) / (loops + alpha + beta)
        score = (p ** gamma) * math.exp(-k * (miss / loops))
    return round(float(score), 3)
"""


def load_task(path: Path) -> dict:
    with path.open("rb") as f:
        data = tomllib.load(f)

    required = ["task", "grader", "prompt"]

    for key in required:
        if key not in data:
            raise ValueError(f"{path.name}: missing [{key}] section")

    # Validate loops
    task_cfg = data["task"]

    category = task_cfg.get("category")
    if not isinstance(category, str) or not category.strip():
        raise ValueError(f"{path.name}: [task].category is required")
    category = category.strip()

    task_name = task_cfg.get("name")
    if not isinstance(task_name, str) or not task_name.strip():
        raise ValueError(f"{path.name}: [task].name is required")
    task_name = task_name.strip()
    if task_name[0].isdigit() or task_name.startswith(INVALID_TASK_NAME_PREFIXES):
        raise ValueError(f"{path.name}: [task].name must not include a difficulty or numeric prefix")

    difficulty = task_cfg.get("difficulty")
    if not isinstance(difficulty, str) or not difficulty.strip():
        raise ValueError(f"{path.name}: [task].difficulty is required")
    difficulty = difficulty.strip()
    if difficulty not in DIFFICULTY_NUMBERS:
        allowed = ", ".join(DIFFICULTY_NUMBERS)
        raise ValueError(f"{path.name}: [task].difficulty must be one of {allowed}")

    task_cfg["name"] = task_name
    task_cfg["difficulty"] = difficulty
    task_cfg["category"] = category

    autopush = task_cfg.get("autopush", False)
    if not isinstance(autopush, bool):
        raise ValueError(f"{path.name}: [task].autopush must be a boolean")
    task_cfg["autopush"] = autopush

    return data


def build_choice_grader(grader: dict, require_choice_only: bool = False) -> str:
    answers = grader.get("answers")
    if not answers:
        raise ValueError("[grader] answers is required")

    answers_repr = repr(set(answers))
    max_length = grader.get("max_length")

    lines = []

    lines.append("        response = llm.prompt(prompt).strip()")
    lines.append("")
    lines.append("        first_token = normalize_choice(response)")
    lines.append("")

    if require_choice_only:
        lines.append(f"        is_correct = response in {answers_repr}")
    elif max_length is not None:
        lines.append(f"        if len(response) > {max_length}:")
        lines.append("            is_correct = True")
        lines.append("        else:")
        lines.append(f"            is_correct = first_token in {answers_repr}")
    else:
        lines.append(f"        is_correct = first_token in {answers_repr}")

    lines.append("")
    lines.append("        if is_correct:")
    lines.append("            pass_count += 1")

    return "\n".join(lines)


def build_forbidden_choice_grader(grader: dict) -> str:
    forbidden = grader.get("forbidden")
    if not forbidden:
        raise ValueError("[grader] forbidden is required")

    forbidden_repr = repr(set(forbidden))

    lines = []
    lines.append("        response = llm.prompt(prompt).strip()")
    lines.append("")
    lines.append("        first_token = normalize_choice(response)")
    lines.append("")
    lines.append(f"        is_correct = first_token not in {forbidden_repr}")
    lines.append("")
    lines.append("        if is_correct:")
    lines.append("            pass_count += 1")

    return "\n".join(lines)


def load_config() -> dict:
    with (ROOT / "config.toml").open("rb") as f:
        return tomllib.load(f)


def load_manifest() -> dict | None:
    manifest_path = BUILD_DIR / "manifest.json"
    if not manifest_path.exists():
        return None

    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def render_task(data: dict, config: dict) -> str:
    task = data["task"]
    grader = data["grader"]
    prompt = data["prompt"]

    task_name = task["name"]
    difficulty = task["difficulty"]
    category = task["category"]

    # Kaggle task ID (immutable)
    kaggle_task_id = f"AUPB_{task_name}"
    # Local task ID (for debugging)
    debug_task_id = f"{category}_{difficulty}_{task_name}"

    loops = config.get("loops", {}).get(difficulty, 1)
    scoring = config["scoring"]
    k = config.get("k", {}).get(difficulty, scoring.get("k", 2.0))
    # debug はトップレベルと [scoring] のどちらでも指定できるようにする
    debug_enabled = bool(config.get("debug", scoring.get("debug", False)))

    function_name = task_name.lower().replace("-", "_").replace(" ", "_")

    grader_type = grader["type"]

    if grader_type == "choice":
        require_choice_only = grader.get("require_choice_only", scoring.get("require_choice_only", False))
        grader_code = build_choice_grader(grader, require_choice_only)
    elif grader_type == "forbidden_choice":
        grader_code = build_forbidden_choice_grader(grader)
    else:
        raise ValueError(f"Unknown grader type: {grader_type}")

    system_prompt = prompt.get("system", "").strip()
    user_prompt = prompt.get("user", "").strip()

    if system_prompt:
        prompt_text = system_prompt + "\n\n" + user_prompt
    else:
        prompt_text = user_prompt

    common_functions = COMMON_FUNCTIONS_TEMPLATE.format(
        method=scoring.get("method", "custom"), alpha=scoring["alpha"], beta=scoring["beta"], gamma=scoring["gamma"], k=k
    )

    # Debug block
    if debug_enabled:
        loop_var = "i"
    else:
        loop_var = "_"

    debug_code = ""
    if debug_enabled:
        debug_code = f"""
        current_fail = ({loop_var} + 1) - pass_count
        current_rate = pass_count / ({loop_var} + 1)
        current_score = calculate_score(pass_count, {loop_var} + 1)
        print(f"Task: {{debug_task_id}} | Diff: {{difficulty}} | Loop: {{ {loop_var} + 1 }}/{{loops}} | Result: {{'Pass' if is_correct else 'Fail'}} | Pass: {{pass_count}} | Fail: {{current_fail}} | Rate: {{current_rate:.3f}} | Score: {{current_score:.3f}}")
"""

    debug_vars = ""
    if debug_enabled:
        debug_vars = f"""
    debug_task_id = {debug_task_id!r}
    difficulty = {difficulty!r}
"""

    return f'''{COMMON_IMPORTS}


{common_functions}


@kbench.task(name="{kaggle_task_id}")
def {function_name}(llm):

    prompt = {prompt_text!r}
{debug_vars}
    loops = {loops}
    pass_count = 0

    for {loop_var} in range(loops):
{grader_code}
{debug_code if debug_enabled else ""}

    return calculate_score(pass_count, loops)


{function_name}.run(kbench.llm)
'''


def write_task(source: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8")


def write_manifest(tasks: list[dict]) -> None:
    manifest = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "tasks": tasks,
    }

    manifest_path = BUILD_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_task_plans(config: dict) -> list[dict]:
    task_plans: list[dict] = []

    for toml_file in sorted(TASK_DIR.glob("*.toml")):
        try:
            data = load_task(toml_file)

            source = render_task(data, config)

            task_cfg = data["task"]
            difficulty = task_cfg["difficulty"]
            category = task_cfg["category"]
            loops = config.get("loops", {}).get(difficulty, 1)
            output_name = f"AUPB_{task_cfg['name']}.py"
            output_file = OUTPUT_DIR / output_name

            task_plans.append(
                {
                    "toml_file": toml_file,
                    "source": source,
                    "output_file": output_file,
                    "manifest_entry": {
                        "name": task_cfg["name"],
                        "difficulty": difficulty,
                        "loops": loops,
                        "autopush": task_cfg["autopush"],
                        "input": toml_file.relative_to(ROOT).as_posix(),
                        "output": f"generated/{output_name}",
                        "hash": hashlib.sha1(source.encode("utf-8")).hexdigest(),
                    },
                }
            )
        except Exception as e:
            print(f"[ERROR] {toml_file.name}")
            print(f"  {e}")

    return task_plans


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def build_all(clean: bool = False, dry_run: bool = False) -> None:
    config = load_config()
    task_plans = build_task_plans(config)
    manifest_tasks = [plan["manifest_entry"] for plan in task_plans]
    current_outputs = {plan["output_file"].as_posix() for plan in task_plans}
    previous_manifest = load_manifest() or {"tasks": []}
    previous_outputs = {
        (ROOT / task["output"]).as_posix()
        for task in previous_manifest.get("tasks", [])
        if isinstance(task, dict) and isinstance(task.get("output"), str)
    }

    if clean:
        delete_targets = sorted(OUTPUT_DIR.iterdir()) if OUTPUT_DIR.exists() else []
        if dry_run:
            for path in delete_targets:
                print(f"DELETE {path.relative_to(ROOT).as_posix()}")
        else:
            if OUTPUT_DIR.exists():
                shutil.rmtree(OUTPUT_DIR)
            OUTPUT_DIR.mkdir(exist_ok=True)
    else:
        delete_targets = [Path(path) for path in sorted(previous_outputs - current_outputs)]
        if dry_run:
            for path in delete_targets:
                print(f"DELETE {path.relative_to(ROOT).as_posix()}")
        else:
            for path in delete_targets:
                if path.exists():
                    remove_path(path)

    count = len(task_plans)
    for plan in task_plans:
        toml_file = plan["toml_file"]
        output_file = plan["output_file"]
        source = plan["source"]
        needs_write = clean or not output_file.exists() or output_file.read_text(encoding="utf-8") != source

        if dry_run:
            if needs_write:
                print(f"WRITE {output_file.relative_to(ROOT).as_posix()}")
        else:
            if needs_write:
                write_task(source, output_file)
                print(f"[OK] {toml_file.name} -> {output_file.name}")
    if dry_run:
        print(f"WRITE {(OUTPUT_DIR / 'manifest.json').relative_to(ROOT).as_posix()}")
        return

    print()
    print(f"Generated {count} task(s).")
    write_manifest(manifest_tasks)
    print(f"Wrote manifest -> {(BUILD_DIR / 'manifest.json').as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="既存の generated を全削除してから生成する")
    parser.add_argument("--dry-run", action="store_true", help="削除・生成予定のみ表示する")
    args = parser.parse_args()

    build_all(clean=args.clean, dry_run=args.dry_run)

    subprocess.run(["ruff", "format", "generated"], check=True)
    subprocess.run(["ruff", "check", "generated", "--fix"], check=True)


if __name__ == "__main__":
    main()
