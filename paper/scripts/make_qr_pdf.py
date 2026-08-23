# QR コードの PDF を生成する(ローカル用の一時スクリプト)。
# SVG → Inkscape 変換の代わりに、lualatex + qrcode パッケージで
# 直接 PDF を出力する。generate_qr_svg.py と同じ TeX 実装を使用。
# 使い方: uv run python paper/scripts/make_qr_pdf.py

import shutil
import subprocess
import tempfile
from pathlib import Path

CONTENT = "https://x.gd/aughx"
OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "aup_benchmark_qr.pdf"

TEX_SOURCE = rf"""\documentclass[border=4mm]{{standalone}}
\usepackage{{qrcode}}
\begin{{document}}
\qrcode[level=H,height=33mm]{{{CONTENT}}}
\end{{document}}
"""


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aup-qr-") as tmp:
        work = Path(tmp)
        tex = work / "qr.tex"
        tex.write_text(TEX_SOURCE, encoding="utf-8")
        result = subprocess.run(
            ["lualatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(result.stdout + result.stderr)
        pdf = work / "qr.pdf"
        if not pdf.exists():
            raise SystemExit("PDF が生成されませんでした")
        # テンポラリと出力先が別ドライブのことがあるため shutil.move を使う
        shutil.move(str(pdf), str(OUTPUT))
    print(f"生成完了: {OUTPUT}")


if __name__ == "__main__":
    main()
