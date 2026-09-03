"""results/ 以下の集計CSVから、ウェブサイト用のデータと画像を自動生成する。

生成物:
    - src/data/results.json : 各ページの表・ハイライト数値のソース
    - public/results/*.png  : グラフ画像(raw.githubusercontent 直参照をやめ、サイト内配布に統一)

使い方(website/ ディレクトリで実行):
    uv run scripts/generate_results.py

前提: リポジトリ直下の results/ と tasks/ が存在すること(aggregate.py の実行後)。
標準ライブラリのみで動作する。
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

# --- パス定義 ---------------------------------------------------------------
WEBSITE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = WEBSITE_DIR.parent
RESULTS_DIR = REPO_DIR / "results"
# 論文図の生成先(gitignore 済み。paper_figures.py が aggregate.py の集計から出力する)
FIGURES_DIR = REPO_DIR / "paper" / "dist" / "figures"
TASKS_DIR = REPO_DIR / "tasks"
OUT_JSON = WEBSITE_DIR / "src" / "data" / "results.json"
OUT_IMG_DIR = WEBSITE_DIR / "public" / "results"

# カテゴリの表示順(論文の分類順に固定)
CATEGORY_ORDER = ["Bias", "Ethics", "Logic", "Robustness", "Safety"]

# コピーするグラフ画像(結果ディレクトリ内のパス → 公開ディレクトリ内のファイル名)
# paper_* は paper_figures.py(論文と同一ロジック)が出力する公式図。
PNG_SOURCES: dict[Path, str] = {
    RESULTS_DIR / "overall_score" / "overall_score.png": "overall_score.png",
    RESULTS_DIR / "overall" / "category_scores.png": "category_scores.png",
    RESULTS_DIR / "pressure_gap" / "pressure_resistance.png": "pressure_resistance.png",
    RESULTS_DIR / "pressure_gap" / "pressure_gap_scores.png": "pressure_gap_scores.png",
    RESULTS_DIR / "pressure_gap" / "pressure_gap_delta.png": "pressure_gap_delta.png",
    RESULTS_DIR / "heatmap" / "heatmap_gap.png": "heatmap_gap.png",
    RESULTS_DIR / "heatmap" / "heatmap_pressure.png": "heatmap_pressure.png",
    FIGURES_DIR / "overall_condition_scores.png": "paper_overall_condition_scores.png",
    FIGURES_DIR / "task_score_drops.png": "paper_task_score_drops.png",
    FIGURES_DIR / "model_condition_scores.png": "paper_model_condition_scores.png",
}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """BOM 付き CSV を読み込み、辞書のリストとして返す。"""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def as_float(row: dict[str, str], key: str) -> float | None:
    """空欄をNoneとしてCSVの数値を読み込む。"""
    value = row.get(key, "")
    return float(value) if value not in (None, "") else None


def main() -> None:
    if not RESULTS_DIR.is_dir():
        sys.exit(f"results ディレクトリが見つかりません: {RESULTS_DIR}")

    # --- 総合スコア(スコア降順) -------------------------------------------
    scores = [
        {"model": row["Model"], "score": float(row["Overall_Score"]), "date": row["Evaluation_Date"]}
        for row in read_csv_rows(RESULTS_DIR / "overall_score" / "overall_score.csv")
    ]
    scores.sort(key=lambda item: item["score"], reverse=True)
    model_order = [item["model"] for item in scores]

    # --- 平常時 vs 圧力下のギャップ(overall_summary.csv) --------------------
    summary_rows = {row["Model"]: row for row in read_csv_rows(RESULTS_DIR / "overall" / "overall_summary.csv")}
    missing = [m for m in model_order if m not in summary_rows]
    if missing:
        sys.exit(f"overall_summary.csv に存在しないモデルがあります: {missing}")
    gap = [
        {
            "model": model,
            "normal": float(summary_rows[model]["Avg Normal"]),
            "pressure": float(summary_rows[model]["Avg Pressure"]),
            "delta": float(summary_rows[model]["Avg Δ (Gap)"]),
            "resistance": float(summary_rows[model]["Pressure Resistance Ratio"]),
            "normalCI": [
                as_float(summary_rows[model], "Avg_Normal_CI_Lower"),
                as_float(summary_rows[model], "Avg_Normal_CI_Upper"),
            ],
            "pressureCI": [
                as_float(summary_rows[model], "Avg_Pressure_CI_Lower"),
                as_float(summary_rows[model], "Avg_Pressure_CI_Upper"),
            ],
            "deltaCI": [
                as_float(summary_rows[model], "Avg_Gap_CI_Lower"),
                as_float(summary_rows[model], "Avg_Gap_CI_Upper"),
            ],
        }
        for model in model_order
    ]

    # 対応のある検定結果(モデル平均・タスク平均)もサイトへ渡す。
    tests_path = RESULTS_DIR / "statistics" / "statistical_tests.csv"
    if not tests_path.is_file():
        sys.exit(f"統計検定結果が見つかりません: {tests_path}\n先に `uv run aggregate.py` を実行してください。")
    statistical_tests = [
        {
            "comparison": row["Comparison"],
            "pairedUnit": row["Paired_Unit"],
            "n": as_float(row, "N"),
            "meanNormal": as_float(row, "Mean_Normal"),
            "meanPressure": as_float(row, "Mean_Pressure"),
            "meanGap": as_float(row, "Mean_Gap"),
            "gapCI": [as_float(row, "Gap_CI_Lower"), as_float(row, "Gap_CI_Upper")],
            "pairedT": as_float(row, "Paired_t"),
            "pairedTDf": as_float(row, "Paired_t_df"),
            "pairedTPvalue": as_float(row, "Paired_t_pvalue"),
            "wilcoxonPvalue": as_float(row, "Wilcoxon_pvalue"),
        }
        for row in read_csv_rows(tests_path)
    ]

    # --- カテゴリ別得点(行=カテゴリ固定順、列=スコア降順モデル) -------------
    category_rows = read_csv_rows(RESULTS_DIR / "overall" / "category_scores.csv")
    unknown_categories = [row["Category"] for row in category_rows if row["Category"] not in CATEGORY_ORDER]
    if unknown_categories:
        sys.exit(f"想定外のカテゴリがあります(CATEGORY_ORDER に追加してください): {unknown_categories}")
    category_rows.sort(key=lambda row: CATEGORY_ORDER.index(row["Category"]))
    category_matrix = {
        "categories": [row["Category"] for row in category_rows],
        "models": model_order,
        # values[カテゴリIndex][モデルIndex]
        "values": [[float(row[model]) for model in model_order] for row in category_rows],
    }

    # --- メタ情報 ------------------------------------------------------------
    updated = max(item["date"] for item in scores)[:10]  # YYYY-MM-DD
    meta = {
        "updated": updated,
        "models": len(scores),
        "tasks": len(list(TASKS_DIR.glob("*.toml"))),
        "categories": CATEGORY_ORDER,
        # 表示側(HeroStat)が小数 3 桁で整形するため、誤差除去程度の丸めに留める
        "bestResistance": round(max(item["resistance"] for item in gap), 4),
    }

    # --- JSON 書き出し --------------------------------------------------------
    payload = {
        "meta": meta,
        "overall": scores,
        "gap": gap,
        "statistics": {"tests": statistical_tests},
        "categoryMatrix": category_matrix,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- グラフ画像のコピー ----------------------------------------------------
    # 前回生成分を丸ごと削除してからコピーする(ソース側で画像が廃止・リネーム
    # されたとき、古い PNG がサイトに残り続けるのを防ぐ)。
    if OUT_IMG_DIR.exists():
        shutil.rmtree(OUT_IMG_DIR)
    OUT_IMG_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src, dest_name in PNG_SOURCES.items():
        if not src.is_file():
            if src.parent == FIGURES_DIR:
                sys.exit(
                    f"論文の図が見つかりません: {src}\n"
                    "先に `uv run aggregate.py` → `uv run paper_figures.py` を実行してください。"
                )
            sys.exit(f"画像が見つかりません(aggregate.py の再実行を検討してください): {src}")
        shutil.copy2(src, OUT_IMG_DIR / dest_name)
        copied += 1

    print(f"[OK] {OUT_JSON.relative_to(WEBSITE_DIR)} を生成(モデル {meta['models']} 件・更新 {updated})")
    print(f"[OK] {copied} 枚の画像を {OUT_IMG_DIR.relative_to(WEBSITE_DIR)} へコピー")


if __name__ == "__main__":
    main()
