from __future__ import annotations

import tomllib
from pathlib import Path
import math

ROOT = Path(__file__).parent
TASK_DIR = ROOT / "tasks"
OUTPUT_DIR = ROOT / "generated"

OUTPUT_DIR.mkdir(exist_ok=True)

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

    task_id = data.get("id", "unknown")
    difficulty = task_id.split("_")[0]
    task_name = task["name"]
    loops = task["loops"]

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

    scoring = config["scoring"]
    common_functions = COMMON_FUNCTIONS_TEMPLATE.format(
        alpha=scoring["alpha"], beta=scoring["beta"], gamma=scoring["gamma"], k=scoring["k"]
    )

    # Debug block
    debug_code = ""
    if config.get("debug", False):
        debug_code = f"""
        current_fail = ({loop_var} + 1) - pass_count
        current_rate = pass_count / ({loop_var} + 1)
        current_score = calculate_score(pass_count, {loop_var} + 1)
        print(f"Task: {{task_id}} | Diff: {{difficulty}} | Loop: {{ {loop_var} + 1 }}/{{loops}} | Result: {{'Pass' if is_correct else 'Fail'}} | Pass: {{pass_count}} | Fail: {{current_fail}} | Rate: {{current_rate:.3f}} | Score: {{current_score:.3f}}")
"""
        # The loop needs to be 'for i in range(loops):' instead of 'for _ in range(loops):'
        loop_var = "i"
    else:
        loop_var = "_"

    return f'''{COMMON_IMPORTS}


{common_functions}


@kbench.task(name="{task_name}")
def {function_name}(llm):

    prompt = {prompt_text!r}
    task_id = {task_id!r}
    difficulty = {difficulty!r}
    loops = {loops}
    pass_count = 0

    for {loop_var} in range(loops):
{grader_code}
{debug_code if config.get("debug", False) else ""}

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

            output_file = OUTPUT_DIR / (toml_file.stem + ".py")
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
