#!/usr/bin/env python3
"""Generate the paper's QR code as an SVG with error correction level H.

This script deliberately uses the TeX Live ``qrcode`` implementation that is
already available in the paper's build environment, then converts its vector
PDF output to SVG with Inkscape.  No third-party Python package is required.
"""

from __future__ import annotations

import argparse
import re
import shutil
import statistics
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_CONTENT = "https://x.gd/aughx"
DEFAULT_OUTPUT = Path("assets/aup_benchmark_qr.svg")
ERROR_CORRECTION = "H"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a QR-code SVG for the AUPB public page.")
    parser.add_argument(
        "--content",
        default=DEFAULT_CONTENT,
        help="Text or URL to encode (default: the AUPB public page)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"SVG output path (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def require_command(name: str) -> str:
    command = shutil.which(name)
    if command is None:
        raise RuntimeError(f"Required command was not found: {name}")
    return command


def run(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        details = completed.stdout + completed.stderr
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}\n{details}")
    return completed.stdout + completed.stderr


def make_tex_source(content: str) -> str:
    # The current URL contains no TeX-special characters.  Reject rather than
    # silently encode the wrong payload if a future value does contain one.
    forbidden = set("#%{}\\")
    found = sorted(forbidden.intersection(content))
    if found:
        characters = " ".join(repr(char) for char in found)
        raise ValueError(f"QR content contains TeX-special characters unsupported by this generator: {characters}")

    return rf"""\documentclass[border=4mm]{{standalone}}
\usepackage{{qrcode}}
\begin{{document}}
\qrcode[level={ERROR_CORRECTION},height=40mm]{{{content}}}
\end{{document}}
"""


def write_compact_svg(source_path: Path, output_path: Path, content: str) -> None:
    """Convert Inkscape's individual module paths into a compact QR grid."""
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    source_root = ET.parse(source_path).getroot()
    namespace = "{http://www.w3.org/2000/svg}"
    number_pattern = re.compile(r"-?(?:\d+(?:\.\d*)?|\.\d+)")

    boxes: list[tuple[float, float, float, float]] = []
    for path in source_root.findall(f"{namespace}path"):
        numbers = [float(value) for value in number_pattern.findall(path.get("d", ""))]
        if len(numbers) < 8 or len(numbers) % 2:
            continue
        coordinates = list(zip(numbers[0::2], numbers[1::2]))
        xs = [point[0] for point in coordinates]
        ys = [point[1] for point in coordinates]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))

    if not boxes:
        raise RuntimeError("No QR modules were found in the converted SVG.")

    module_size = statistics.median(min(right - left, bottom - top) for left, top, right, bottom in boxes)
    left_edge = min(box[0] for box in boxes)
    top_edge = min(box[1] for box in boxes)

    modules = {
        (
            round((left - left_edge) / module_size),
            round((top - top_edge) / module_size),
        )
        for left, top, _, _ in boxes
    }
    module_count = max(max(x for x, _ in modules), max(y for _, y in modules)) + 1
    if module_count < 21 or (module_count - 21) % 4 != 0:
        raise RuntimeError(f"Unexpected QR module count: {module_count}")

    quiet_zone = 4
    side_length = module_count + 2 * quiet_zone
    commands: list[str] = []
    for row in range(module_count):
        columns = sorted(x for x, y in modules if y == row)
        if not columns:
            continue
        run_start = run_end = columns[0]
        for column in columns[1:] + [module_count + 1]:
            if column == run_end + 1:
                run_end = column
                continue
            x = quiet_zone + run_start
            y = quiet_zone + row
            width = run_end - run_start + 1
            commands.append(f"M{x} {y}h{width}v1h-{width}z")
            run_start = run_end = column

    root = ET.Element(
        f"{namespace}svg",
        {
            "width": f"{side_length}mm",
            "height": f"{side_length}mm",
            "viewBox": f"0 0 {side_length} {side_length}",
            "role": "img",
            "aria-label": "QR code for the AUPB public page",
            "shape-rendering": "crispEdges",
            "data-error-correction": ERROR_CORRECTION,
            "data-qr-version": str((module_count - 17) // 4),
            "data-content": content,
        },
    )
    title = ET.SubElement(root, f"{namespace}title")
    title.text = "AUPB public page QR code"
    ET.SubElement(
        root,
        f"{namespace}rect",
        {
            "width": str(side_length),
            "height": str(side_length),
            "fill": "#ffffff",
        },
    )
    ET.SubElement(
        root,
        f"{namespace}path",
        {"d": "".join(commands), "fill": "#000000"},
    )
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)


def generate_svg(content: str, output_path: Path) -> None:
    lualatex = require_command("lualatex")
    inkscape = require_command("inkscape")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path = output_path.resolve()

    with tempfile.TemporaryDirectory(prefix="aup-qr-") as temporary_directory:
        work_dir = Path(temporary_directory)
        tex_path = work_dir / "qr.tex"
        pdf_path = work_dir / "qr.pdf"
        svg_path = work_dir / "qr.svg"

        tex_path.write_text(make_tex_source(content), encoding="utf-8")
        latex_output = run(
            [
                lualatex,
                "-interaction=nonstopmode",
                "-halt-on-error",
                tex_path.name,
            ],
            cwd=work_dir,
        )
        if not re.search(r"Calculating QR code.*version \d+-H", latex_output):
            raise RuntimeError("The QR generator did not confirm error correction level H.")
        run(
            [
                inkscape,
                str(pdf_path),
                "--pdf-poppler",
                "--export-plain-svg",
                f"--export-filename={svg_path}",
            ],
            cwd=work_dir,
        )

        write_compact_svg(svg_path, output_path, content)

    print(f"Generated {output_path} (error correction: {ERROR_CORRECTION})")


def main() -> None:
    args = parse_args()
    generate_svg(args.content, args.output)


if __name__ == "__main__":
    main()
