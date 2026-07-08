from __future__ import annotations

import tomllib
from pathlib import Path
import math

ROOT = Path(__file__).parent
TASK_DIR = ROOT / "tasks"
OUTPUT_DIR = ROOT / "generated"

OUTPUT_DIR.mkdir(exist_ok=True)

DIFFICULTY_NUMBERS = {
    "E": 1,
    "M": 2,
    "H": 3,
    "INS": 4,
    "INS+": 5,
}

INVALID_TASK_NAME_PREFIXES = tuple(f"{difficulty}_" for difficulty in DIFFICULTY_NUMBERS)

COMMON_IMPORTS = """import re
import math
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

    loops = task_cfg.get("loops", 1)
    if not isinstance(loops, int) or loops <= 0:
        raise ValueError(f"{path.name}: [task] loops must be a positive integer")
    task_cfg["loops"] = loops

    return data


def build_choice_grader(grader: dict) -> str:
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

    if max_length is not None:
        lines.append(f"        if len(response) > {max_length}:")
        lines.append("            is_correct = False")
        lines.append("        else:")
        lines.append(f"            is_correct = first_token in {answers_repr}")
    else:
        lines.append(f"        is_correct = first_token in {answers_repr}")

    lines.append("")
    lines.append("        if is_correct:")
    lines.append("            pass_count += 1")

    return "\n".join(lines)


def load_config() -> dict:
    with (ROOT / "config.toml").open("rb") as f:
        return tomllib.load(f)


def render_task(data: dict, config: dict) -> str:
    task = data["task"]
    grader = data["grader"]
    prompt = data["prompt"]

    task_name = task["name"]
    difficulty = task["difficulty"]
    task_id = f"{difficulty}_{task_name}"
    loops = task["loops"]
    scoring = config["scoring"]
    # debug はトップレベルと [scoring] のどちらでも指定できるようにする
    debug_enabled = bool(config.get("debug", scoring.get("debug", False)))

    function_name = task_name.lower().replace("-", "_").replace(" ", "_")

    grader_type = grader["type"]

    if grader_type == "choice":
        grader_code = build_choice_grader(grader)
    else:
        raise ValueError(f"Unknown grader type: {grader_type}")

    system_prompt = prompt.get("system", "").strip()
    user_prompt = prompt.get("user", "").strip()

    if system_prompt:
        prompt_text = system_prompt + "\n\n" + user_prompt
    else:
        prompt_text = user_prompt

    common_functions = COMMON_FUNCTIONS_TEMPLATE.format(
        alpha=scoring["alpha"], beta=scoring["beta"], gamma=scoring["gamma"], k=scoring["k"]
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
        print(f"Task: {{task_id}} | Diff: {{difficulty}} | Loop: {{ {loop_var} + 1 }}/{{loops}} | Result: {{'Pass' if is_correct else 'Fail'}} | Pass: {{pass_count}} | Fail: {{current_fail}} | Rate: {{current_rate:.3f}} | Score: {{current_score:.3f}}")
"""

    debug_vars = ""
    if debug_enabled:
        debug_vars = f"""
    task_id = {task_id!r}
    difficulty = {difficulty!r}
"""

    return f'''{COMMON_IMPORTS}


{common_functions}


@kbench.task(name="{task_id}")
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


def build_all() -> None:
    count = 0
    config = load_config()

    for toml_file in sorted(TASK_DIR.glob("*.toml")):
        try:
            data = load_task(toml_file)

            source = render_task(data, config)

            task_cfg = data["task"]
            output_file = (
                OUTPUT_DIR
                / f"{DIFFICULTY_NUMBERS[task_cfg['difficulty']]}_{task_cfg['difficulty']}_{task_cfg['name']}.py"
            )
            write_task(source, output_file)

            print(f"[OK] {toml_file.name} -> {output_file.name}")
            count += 1

        except Exception as e:
            print(f"[ERROR] {toml_file.name}")
            print(f"  {e}")

    print()
    print(f"Generated {count} task(s).")


def main() -> None:
    build_all()


if __name__ == "__main__":
    main()
