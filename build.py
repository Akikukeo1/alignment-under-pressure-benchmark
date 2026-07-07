from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parent
TASK_DIR = ROOT / "tasks"
OUTPUT_DIR = ROOT / "generated"

OUTPUT_DIR.mkdir(exist_ok=True)

COMMON_IMPORTS = """import re
import kaggle_benchmarks as kbench
"""

COMMON_FUNCTIONS = r"""
def normalize_choice(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    if not text:
        return ""
    token = text.split()[0]
    return token.strip(").,:;\"'")
"""


def load_task(path: Path) -> dict:
    with path.open("rb") as f:
        data = tomllib.load(f)

    required = ["task", "grader", "prompt"]

    for key in required:
        if key not in data:
            raise ValueError(f"{path.name}: missing [{key}] section")

    return data


def build_choice_grader(grader: dict) -> str:
    answers = grader.get("answers")
    if not answers:
        raise ValueError("[grader] answers is required")

    answers_repr = repr(set(answers))
    max_length = grader.get("max_length")

    lines = []

    lines.append("    response = llm.prompt(prompt).strip()")
    lines.append("")
    lines.append("    first_token = normalize_choice(response)")
    lines.append("")

    if max_length is not None:
        lines.append(f"    if len(response) > {max_length}:")
        lines.append("        is_correct = False")
        lines.append("    else:")
        lines.append(f"        is_correct = first_token in {answers_repr}")
    else:
        lines.append(f"    is_correct = first_token in {answers_repr}")

    lines.append("")
    lines.append("    kbench.assertions.assert_true(")
    lines.append("        is_correct,")
    lines.append(f"        expectation=f\"Expected one of {sorted(answers)}, got '{{response}}'\"")
    lines.append("    )")

    return "\n".join(lines)


def render_task(data: dict) -> str:
    task = data["task"]
    grader = data["grader"]
    prompt = data["prompt"]

    task_name = task["name"]

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

    return f'''{COMMON_IMPORTS}


{COMMON_FUNCTIONS}


@kbench.task(name="{task_name}")
def {function_name}(llm):

    prompt = {prompt_text!r}

{grader_code}


{function_name}.run(kbench.llm)
'''


def write_task(source: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8")


def build_all() -> None:
    count = 0

    for toml_file in sorted(TASK_DIR.glob("*.toml")):
        try:
            data = load_task(toml_file)

            source = render_task(data)

            output_file = OUTPUT_DIR / (toml_file.stem + ".py")
            write_task(source, output_file)

            print(f"✓ {toml_file.name} -> {output_file.name}")
            count += 1

        except Exception as e:
            print(f"✗ {toml_file.name}")
            print(f"  {e}")

    print()
    print(f"Generated {count} task(s).")


def main() -> None:
    build_all()


if __name__ == "__main__":
    main()
