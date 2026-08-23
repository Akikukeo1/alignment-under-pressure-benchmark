"""リポジトリ直下の REPRODUCIBILITY.md から、ウェブサイト用の再現手順ページを自動生成する。

生成物:
    - src/content/docs/reproducibility.mdx : Starlight のドキュメントページ

REPRODUCIBILITY.md を正本とし、以下の変換を行ってサイト向けに同期する:
    - frontmatter(title / description / slug)の付与
    - 先頭の H1 見出しの除去(frontmatter の title と二重になるため)
    - GitHub 内相対リンクの絶対 URL への置換(外部リンクと分かるようラベルに (GitHub ↗) を付与)
    - Mermaid 図のブロックを「GitHub で見る」Aside への置換(サイト側では描画できないため。
      GitHub では Mermaid がネイティブ描画されるので正本側は無変更)
    - 冒頭への正本(GitHub)への導線追加

使い方(website/ ディレクトリで実行):
    uv run scripts/generate_repro.py

標準ライブラリのみで動作する。
"""

from __future__ import annotations

import re
from pathlib import Path

# --- パス定義 ---------------------------------------------------------------
WEBSITE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = WEBSITE_DIR.parent
SRC_MD = REPO_DIR / "REPRODUCIBILITY.md"
OUT_MDX = WEBSITE_DIR / "src" / "content" / "docs" / "reproducibility.mdx"

GITHUB_BLOB_BASE = "https://github.com/Akikukeo1/alignment-under-pressure-benchmark/blob/main/"
SRC_MD_URL = f"{GITHUB_BLOB_BASE}REPRODUCIBILITY.md"

FRONTMATTER = """\
---
title: 再現手順
description: AUPB の評価結果をゼロから再現する手順。タスクのビルドから Kaggle 実行、集計まで
slug: reproducibility
---
"""

# ページ冒頭に差し込む正本への導線(サイト固有の文言のためスクリプト側で持つ)
INTRO_NOTE = f"""\
:::note[このページについて]
このページはリポジトリの [REPRODUCIBILITY.md(GitHub ↗)]({SRC_MD_URL}) から自動生成しています。
最新の内容は GitHub 側が正本です。
:::
"""


def strip_leading_h1(text: str) -> str:
    """先頭の H1 見出し(# で始まる行と直後の空行)を取り除く。

    Starlight は frontmatter の title をページ見出しとして描画するため、
    本文側の H1 があるとタイトルが二重になる。
    """
    return re.sub(r"\A# [^\n]*\n+", "", text)


def rewrite_relative_links(text: str) -> str:
    """GitHub 内相対リンク([label](path) 形式)を絶対 URL に置換する。

    対象は `http(s)://`・`/`・`#` で始まらないリンクのみ。サイト外(GitHub)へ
    出ていくことが分かるよう、ラベル末尾に「(GitHub ↗)」を付ける。
    アンカー付き(例: docs/TASK_SCHEMA.md#難易度)もそのまま URL に引き継ぐ。
    """
    pattern = re.compile(r"\[([^\]]+)\]\((?!https?://|/|#)([^)]+)\)")

    def repl(match: re.Match[str]) -> str:
        label, path = match.group(1), match.group(2)
        return f"[{label}(GitHub ↗)]({GITHUB_BLOB_BASE}{path})"

    return pattern.sub(repl, text)


def replace_mermaid_blocks(text: str) -> str:
    """Mermaid コードブロックを「GitHub で見る」Aside に置換する。

    Starlight には Mermaid 描画機能がなく、コードブロックのまま表示されてしまう。
    図そのものは GitHub がネイティブ描画するため、そちらへ誘導する。
    """
    aside = (
        f":::note[パイプライン図]\n"
        f"パイプライン全体像の図は [GitHub 上の REPRODUCIBILITY.md(GitHub ↗)]({SRC_MD_URL}) "
        f"で描画表示されます。同じ内容を次の表にまとめています。\n"
        f":::\n"
    )
    return re.sub(r"```mermaid\n.*?\n```\n", aside, text, flags=re.DOTALL)


def main() -> None:
    if not SRC_MD.is_file():
        raise SystemExit(f"正本の MD が見つかりません: {SRC_MD}")

    body = SRC_MD.read_text(encoding="utf-8")
    body = strip_leading_h1(body)
    body = rewrite_relative_links(body)
    body = replace_mermaid_blocks(body)

    OUT_MDX.parent.mkdir(parents=True, exist_ok=True)
    OUT_MDX.write_text(FRONTMATTER + INTRO_NOTE + "\n" + body, encoding="utf-8")

    print(f"[OK] {OUT_MDX.relative_to(WEBSITE_DIR)} を生成({SRC_MD.name} から同期)")


if __name__ == "__main__":
    main()
