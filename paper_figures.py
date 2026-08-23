"""論文の図を生成するスクリプト(論文で使用したものと同一ロジック)。

入力CSV(Model / Task_Name / Numerical_Result 列を持つもの)から、
8点満点の条件別得点に関する 3 種類の図を出力する。

使い方(リポジトリ直下で実行):
    uv run paper_figures.py --input akikukeo1_alignment-under-pressure-benchmark_leaderboard.csv
    # 既定値は論文時と同じ result.csv / results/figures/
"""

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_PATH = Path("result.csv")
OUTPUT_DIR = Path("results/figures")

MODEL_LABELS = {
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash Lite",
    "grok-4.20-0309-reasoning": "Grok 4.20（reasoning）",
    "grok-4.20-0309-non-reasoning": "Grok 4.20（non-reasoning）",
    "claude-opus-4-8-default": "Claude Opus 4.8",
    "claude-opus-5-default": "Claude Opus 5",
    "gemini-3.6-flash": "Gemini 3.6 Flash",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "claude-sonnet-4-6-default": "Claude Sonnet 4.6",
    "gpt-5.6-terra": "GPT-5.6 Terra",
    "gemini-3-flash-preview": "Gemini 3 Flash Preview",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gpt-5.4-2026-03-05": "GPT-5.4（2026-03-05）",
}


def load_scores() -> tuple[pd.DataFrame, pd.DataFrame]:
    """モデル別の総合得点と、タスク別の平均得点を返す。"""
    data = pd.read_csv(DATA_PATH)
    tasks = data[data["Task_Name"].notna()].copy()

    tasks["condition"] = np.where(
        tasks["Task_Name"].str.startswith("AUPB_Normal_"),
        "通常条件",
        "圧力条件",
    )
    tasks["task"] = (
        tasks["Task_Name"].str.replace("AUPB_Normal_", "", regex=False).str.replace("AUPB_", "", regex=False)
    )

    if tasks["Numerical_Result"].isna().any():
        raise ValueError("タスクの得点に欠損があります。")
    if not tasks["Numerical_Result"].between(0, 1).all():
        raise ValueError("0点から1点の範囲外にあるタスク得点があります。")
    if tasks.duplicated(["Model", "task", "condition"]).any():
        raise ValueError("同じモデル・タスク・条件の行が重複しています。")

    task_counts = tasks.groupby(["Model", "condition"])["task"].nunique()
    if not task_counts.eq(8).all():
        raise ValueError("8種類のタスクがそろっていないモデルまたは条件があります。")

    totals = tasks.groupby(["Model", "condition"])["Numerical_Result"].sum().unstack()
    task_means = tasks.groupby(["task", "condition"])["Numerical_Result"].mean().unstack()
    task_means["低下幅"] = task_means["通常条件"] - task_means["圧力条件"]
    return totals[["通常条件", "圧力条件"]], task_means


def plot_overall_scores(totals: pd.DataFrame) -> None:
    """12モデルの平均総合得点を8点満点の棒グラフで示す。"""
    labels = ["通常条件", "圧力条件"]
    means = totals[labels].mean()
    difference = means["通常条件"] - means["圧力条件"]

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = np.arange(len(labels))
    colors = ["#9DB7DE", "#B45309"]
    bars = ax.bar(x, means.values, width=0.56, color=colors)

    ax.set_ylim(0, 8)
    ax.set_yticks(np.arange(0, 9, 1))
    ax.set_ylabel("平均得点（8点満点）")
    ax.set_xticks(x, labels)
    ax.set_title("通常条件と圧力条件の平均得点", pad=14, fontweight="bold")
    ax.grid(axis="y", color="#D9DEE3", linewidth=0.8)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, means.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.15,
            f"{value:.1f}点",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
        )

    arrow_x = 0.5
    ax.annotate(
        "",
        xy=(arrow_x, means["圧力条件"] + 0.08),
        xytext=(arrow_x, means["通常条件"] - 0.08),
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#B42318",
            "linewidth": 2.0,
        },
    )
    ax.text(
        arrow_x + 0.06,
        (means["通常条件"] + means["圧力条件"]) / 2,
        f"{difference:.1f}点低下",
        ha="left",
        va="center",
        color="#B42318",
        fontsize=10.5,
        fontweight="bold",
    )

    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#ADB5BD")
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        OUTPUT_DIR / "overall_condition_scores.png",
        dpi=220,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(f"通常条件の平均: {means['通常条件']:.4f} / 8点")
    print(f"圧力条件の平均: {means['圧力条件']:.4f} / 8点")
    print(f"平均低下幅: {difference:.4f}点")


def plot_task_drops(task_means: pd.DataFrame) -> None:
    """8タスクの通常条件から圧力条件への平均低下幅を示す。"""
    scores = task_means.sort_values("低下幅", ascending=True)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    y = np.arange(len(scores))
    bars = ax.barh(y, scores["低下幅"], color="#2457A7", height=0.62)

    ax.set_xlim(0, 1.08)
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_xlabel("平均低下幅（1タスク1点満点）")
    ax.set_yticks(y, scores.index)
    ax.set_title("タスク別の平均低下幅", pad=12, fontweight="bold")
    ax.grid(axis="x", color="#D9DEE3", linewidth=0.8)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, scores["低下幅"]):
        ax.text(
            max(value + 0.018, 0.018),
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}点",
            ha="left",
            va="center",
            fontsize=9.5,
            fontweight="bold" if value >= 0.5 else "normal",
        )

    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#ADB5BD")
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        OUTPUT_DIR / "task_score_drops.png",
        dpi=220,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_model_scores(totals: pd.DataFrame) -> None:
    """モデルごとの通常条件と圧力条件の総合得点を比較する。"""
    scores = totals.copy()
    scores["低下幅"] = scores["通常条件"] - scores["圧力条件"]
    scores = scores.sort_values(["圧力条件", "通常条件"], ascending=[False, False])

    y = np.arange(len(scores))
    fig, ax = plt.subplots(figsize=(8.4, 6.2))
    ax.hlines(
        y,
        scores["圧力条件"],
        scores["通常条件"],
        color="#9AA6B2",
        linewidth=2.0,
    )
    ax.scatter(
        scores["通常条件"],
        y,
        s=58,
        color="#9DB7DE",
        edgecolor="white",
        linewidth=0.7,
        label="通常条件",
        zorder=3,
    )
    ax.scatter(
        scores["圧力条件"],
        y,
        s=58,
        color="#B45309",
        edgecolor="white",
        linewidth=0.7,
        label="圧力条件",
        zorder=3,
    )

    labels = [MODEL_LABELS.get(model, model) for model in scores.index]
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 8.15)
    ax.set_xticks(np.arange(0, 9, 1))
    ax.set_xlabel("総合得点（8点満点）")
    ax.set_title("モデル別の通常条件と圧力条件の得点", pad=12, fontweight="bold")
    ax.grid(axis="x", color="#D9DEE3", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, ncol=2)

    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#ADB5BD")
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        OUTPUT_DIR / "model_condition_scores.png",
        dpi=220,
        bbox_inches="tight",
    )
    plt.close(fig)

    print(f"モデル別の最小低下幅: {scores['低下幅'].min():.4f}点")
    print(f"モデル別の最大低下幅: {scores['低下幅'].max():.4f}点")


def main() -> None:
    global DATA_PATH, OUTPUT_DIR

    parser = argparse.ArgumentParser(description="論文の図を生成する")
    parser.add_argument(
        "--input",
        "-i",
        default=str(DATA_PATH),
        help="入力CSVのパス(既定: result.csv)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(OUTPUT_DIR),
        help="図の出力先ディレクトリ(既定: results/figures)",
    )
    args = parser.parse_args()

    DATA_PATH = Path(args.input)
    OUTPUT_DIR = Path(args.output_dir)

    mpl.rcParams.update({
        "font.family": "sans-serif",
        # Windows 環境でも日本語が描けるようフォールバックを追加
        "font.sans-serif": [
            "Noto Sans CJK JP",
            "Meiryo",
            "Yu Gothic",
            "DejaVu Sans",
        ],
        "axes.unicode_minus": False,
        "font.size": 10,
    })
    totals, task_means = load_scores()
    plot_overall_scores(totals)
    plot_task_drops(task_means)
    plot_model_scores(totals)


if __name__ == "__main__":
    main()
