"""論文の図を生成するスクリプト(描画専任)。

aggregate.py の出力である results/ 以下の集計 CSV を読み込み、論文で使用する
3 種類の図を出力する。数値集計は行わない(集計の SSOT は aggregate.py のみ)。

使い方(リポジトリ直下で実行):
    uv run aggregate.py            # 先に集計を実行しておく(results/ を更新)
    uv run paper_figures.py        # 図 3 枚を paper/dist/figures/ へ出力

入力(results/ 以下・aggregate.py の出力):
    - overall_score/overall_score.csv      : Kaggle 公式 Overall Score
    - overall/overall_summary.csv          : モデル別の平均指標
    - pressure_gap/pressure_gap_by_task.csv: タスク別スコア(Model × Task ロング形式)

出力(paper/dist/figures/ 以下・gitignore 済みのビルド成果物):
    - overall_condition_scores.png : 通常条件と圧力条件の平均得点
    - task_score_drops.png         : タスク別の平均低下幅
    - model_condition_scores.png   : モデル別の通常/圧力条件比較
"""

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RESULTS_DIR = Path("results")
OUTPUT_DIR = Path("paper/dist/figures")

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


def load_aggregates(results_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """aggregate.py の出力からモデル別サマリーとタスク別低下幅を読み込む。

    戻り値:
        model_summary : index=Model、columns=[通常条件, 圧力条件]
                        (overall_summary.csv の Avg Normal / Avg Pressure)
        task_drops    : index=Task、columns=[Avg Normal, Avg Pressure, 低下幅]
                        (pressure_gap_by_task.csv をタスク単位で平均化したもの)
    """
    summary_path = results_dir / "overall" / "overall_summary.csv"
    by_task_path = results_dir / "pressure_gap" / "pressure_gap_by_task.csv"

    if not summary_path.exists():
        raise FileNotFoundError(f"集計結果が見つかりません: {summary_path}。先に uv run aggregate.py を実行してください。")

    model_summary = (
        pd.read_csv(summary_path)
        .set_index("Model")[["Avg Normal", "Avg Pressure"]]
        .rename(columns={"Avg Normal": "通常条件", "Avg Pressure": "圧力条件"})
    )

    task_drops = (
        pd.read_csv(by_task_path).groupby("Task")[["Normal", "Pressure"]].mean()
    ).rename(columns={"Normal": "Avg Normal", "Pressure": "Avg Pressure"})
    task_drops["低下幅"] = task_drops["Avg Normal"] - task_drops["Avg Pressure"]

    return model_summary, task_drops


def plot_overall_scores(model_summary: pd.DataFrame) -> None:
    """全モデル横断の平均得点を棒グラフで示す。"""
    labels = ["通常条件", "圧力条件"]
    means = model_summary[labels].mean()
    difference = means["通常条件"] - means["圧力条件"]

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = np.arange(len(labels))
    colors = ["#9DB7DE", "#B45309"]
    bars = ax.bar(x, means.values, width=0.56, color=colors)

    ax.set_ylim(0, 1.0)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_ylabel("平均得点（1タスクあたり1点満点）")
    ax.set_xticks(x, labels)
    ax.set_title("通常条件と圧力条件の平均得点", pad=14, fontweight="bold")
    ax.grid(axis="y", color="#D9DEE3", linewidth=0.8)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, means.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.015,
            f"{value:.3f}",
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
        )

    arrow_x = 0.5
    ax.annotate(
        "",
        xy=(arrow_x, means["圧力条件"] + 0.008),
        xytext=(arrow_x, means["通常条件"] - 0.008),
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#B42318",
            "linewidth": 2.0,
        },
    )
    ax.text(
        arrow_x + 0.06,
        (means["通常条件"] + means["圧力条件"]) / 2,
        f"{difference:.3f}低下",
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

    print(f"通常条件の平均: {means['通常条件']:.4f}")
    print(f"圧力条件の平均: {means['圧力条件']:.4f}")
    print(f"平均低下幅: {difference:.4f}")


def plot_task_drops(task_drops: pd.DataFrame) -> None:
    """各タスクの通常条件から圧力条件への平均低下幅を示す。"""
    scores = task_drops.sort_values("低下幅", ascending=True)

    # 大きく落ちているタスクを強調(最大低下幅の 7 割以上)
    emphasis_threshold = scores["低下幅"].max() * 0.7

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    y = np.arange(len(scores))
    bars = ax.barh(y, scores["低下幅"], color="#2457A7", height=0.62)

    # 正負両方(圧力で上昇するタスク)を含めて軸範囲を決める
    lo = min(scores["低下幅"].min() * 1.15, 0)
    hi = max(scores["低下幅"].max() * 1.08, 0.05)
    ax.set_xlim(lo, hi)

    # 目盛りは 0.1 刻み・ラベルは小数 1 桁(細かすぎるとラベルが重なるため)
    step = 0.1
    ticks = np.arange(np.floor(lo / step) * step, hi + step / 2, step)
    ax.set_xticks(ticks, [f"{t:.1f}" for t in ticks])
    ax.set_xlabel("平均低下幅（1タスクあたり1点満点）")
    ax.set_yticks(y, scores.index)
    ax.set_title("タスク別の平均低下幅", pad=12, fontweight="bold")
    ax.grid(axis="x", color="#D9DEE3", linewidth=0.8)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, scores["低下幅"]):
        offset = 0.002 if value >= 0 else -0.002
        ax.text(
            value + offset,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.3f}",
            ha="left" if value >= 0 else "right",
            va="center",
            fontsize=9.5,
            fontweight="bold" if value >= emphasis_threshold else "normal",
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


def plot_model_scores(model_summary: pd.DataFrame) -> None:
    """モデルごとの通常条件と圧力条件の平均得点を比較する。"""
    scores = model_summary.copy()
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
    ax.set_xlim(0, 1.05)
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_xlabel("平均得点（1タスクあたり1点満点）")
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

    print(f"モデル別の最小低下幅: {scores['低下幅'].min():.4f}")
    print(f"モデル別の最大低下幅: {scores['低下幅'].max():.4f}")


def main() -> None:
    global RESULTS_DIR, OUTPUT_DIR

    parser = argparse.ArgumentParser(description="論文の図を生成する(aggregate.py の集計結果から)")
    parser.add_argument(
        "--results-dir",
        "-r",
        default=str(RESULTS_DIR),
        help="aggregate.py の出力ディレクトリ(既定: results)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(OUTPUT_DIR),
        help="図の出力先ディレクトリ(既定: paper/dist/figures)",
    )
    args = parser.parse_args()

    RESULTS_DIR = Path(args.results_dir)
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
    model_summary, task_drops = load_aggregates(RESULTS_DIR)
    plot_overall_scores(model_summary)
    plot_task_drops(task_drops)
    plot_model_scores(model_summary)


if __name__ == "__main__":
    main()
