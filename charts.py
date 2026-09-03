"""AUPB のグラフ描画モジュール。

サイト(Cobalt テーマ)と視覚的に揃えた統一スタイルで、results/ 以下の
グラフ画像を生成する。データ処理と CSV 出力は aggregate.py 側で行い、
このモジュールは描画のみを担当する。

設計方針:
    - モデルの色は全グラフで共通(model_colors を経由して必ず同じ色を当てる)
    - 条件色は固定:平常時=グレー / 圧力下=コバルト
    - タイトルに番号を付けない(サイト側の見出しと重複しない)
    - 軸ラベルのモデル名は短縮形(short_model)を使う
    - 図内テキストは日本語(paper_figures.py と同一のフォントフォールバック)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. 統一スタイル定義 (Theme)
# ==========================================

INK = "#1E293B"  # 文字色(濃い墨)
MUTED = "#64748B"  # 補助文字・軸ラベル
GRID = "#E2E8F0"  # グリッド線
SPINE = "#CBD5E1"  # 軸線

ACCENT = "#2563EB"  # 電気コバルト(サイトのアクセント色と共通)
NORMAL_COLOR = "#94A3B8"  # 平常時条件のバー
PRESSURE_COLOR = ACCENT  # 圧力下条件のバー
GOOD = "#059669"  # ギャップ ≥ 0(低下なし)
BAD = "#DC2626"  # ギャップ < 0(性能低下)

# モデルごとの色(全グラフで共通)。モデル数が増えた場合は先頭から順に割り当てる。
MODEL_PALETTE = [
    "#2563EB",  # cobalt
    "#0EA5E9",  # sky
    "#7C3AED",  # violet
    "#059669",  # emerald
    "#D97706",  # amber
    "#DB2777",  # pink
    "#475569",  # slate
    "#0D9488",  # teal
]

FIG_DPI = 200


def short_model(model: str) -> str:
    """軸ラベル用にモデル名を短縮する(-default / -preview を除去)。"""
    return model.removesuffix("-default").removesuffix("-preview")


def setup_style() -> None:
    """全グラフ共通の見た目を適用する(main 冒頭で一度だけ呼ぶ)。"""
    sns.set_theme(
        style="white",
        rc={
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": SPINE,
            "axes.labelcolor": MUTED,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlepad": 14,
            "xtick.labelcolor": INK,
            "ytick.labelcolor": INK,
            "xtick.color": SPINE,
            "ytick.color": SPINE,
            "font.family": "sans-serif",
            # Windows 環境でも日本語が描けるようフォールバックを追加(CI は fonts-noto-cjk)
            "font.sans-serif": [
                "Noto Sans CJK JP",
                "Meiryo",
                "Yu Gothic",
                "DejaVu Sans",
            ],
            "font.size": 11,
            "legend.frameon": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
        },
    )
    plt.rcParams["axes.unicode_minus"] = False


def model_colors(models: list[str]) -> dict[str, str]:
    """モデル名 → 色 の安定マッピングを作る。

    全グラフで同じ呼び出し順(スコア降順など)で渡せば、
    同じモデルには常に同じ色が割り当てられる。
    """
    return {m: MODEL_PALETTE[i % len(MODEL_PALETTE)] for i, m in enumerate(models)}


# ==========================================
# 2. 共通ヘルパー (Helpers)
# ==========================================


def _save(fig: plt.Figure, path: Path) -> None:
    """図を保存して閉じる。"""
    fig.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"[chart] {path.name} を出力しました")


def _grid_axis_only(ax: plt.Axes, axis: str = "x") -> None:
    """指定軸方向だけグリッドを表示する。"""
    other = "y" if axis == "x" else "x"
    ax.grid(True, axis=axis)
    ax.grid(False, axis=other)


def _labels_v(ax: plt.Axes, fmt: str = "{:.2f}", pad_points: int = 2) -> None:
    """縦棒グラフのバー上端に数値ラベルを付ける(0 はスキップ)。"""
    for bar in ax.patches:
        h = bar.get_height()
        if not np.isfinite(h) or h == 0:
            continue
        ax.annotate(
            fmt.format(h),
            (bar.get_x() + bar.get_width() / 2.0, h),
            ha="center",
            va="bottom",
            fontsize=8,
            xytext=(0, pad_points),
            textcoords="offset points",
            color=INK,
        )


def _ci_errors(
    data: pd.DataFrame,
    mean_column: str,
    lower_column: str,
    upper_column: str,
) -> np.ndarray:
    """平均値から95%不確実性区間までの上下の誤差量をmatplotlib形式で返す。"""
    means = data[mean_column].to_numpy(dtype=float)
    lower = data[lower_column].to_numpy(dtype=float)
    upper = data[upper_column].to_numpy(dtype=float)
    lower_error = means - lower
    upper_error = upper - means
    lower_error[~np.isfinite(lower_error)] = 0.0
    upper_error[~np.isfinite(upper_error)] = 0.0
    return np.vstack([np.maximum(lower_error, 0.0), np.maximum(upper_error, 0.0)])


def _se_errors(data: pd.DataFrame, se_column: str) -> np.ndarray:
    """標準誤差をmatplotlibの対称エラーバー形式で返す。"""
    standard_errors = data[se_column].to_numpy(dtype=float, copy=True)
    standard_errors[~np.isfinite(standard_errors)] = 0.0
    return np.vstack([np.maximum(standard_errors, 0.0), np.maximum(standard_errors, 0.0)])


def _labels_v_above_error(
    ax: plt.Axes,
    bars: object,
    upper_errors: np.ndarray,
    fmt: str = "{:.2f}",
) -> None:
    """縦棒の数値ラベルをエラーバーの上端より上に置く。"""
    for bar, upper_error in zip(bars, upper_errors, strict=True):
        height = bar.get_height()
        if not np.isfinite(height):
            continue
        error = upper_error if np.isfinite(upper_error) else 0.0
        ax.annotate(
            fmt.format(height),
            (bar.get_x() + bar.get_width() / 2.0, height + max(error, 0.0)),
            ha="center",
            va="bottom",
            fontsize=8,
            xytext=(0, 2),
            textcoords="offset points",
            color=INK,
        )


# ==========================================
# 3. 個別グラフ (Charts)
# ==========================================


def plot_overall_score(overall_df: pd.DataFrame, path: Path) -> None:
    """総合スコアの横棒グラフ(単色コバルト・数値ラベルで語らせる)。"""
    labels = [short_model(str(m)) for m in overall_df["Model"]]
    ypos = np.arange(len(overall_df))[::-1]  # 1位を上に

    fig, ax = plt.subplots(figsize=(8, 0.6 * len(overall_df) + 1.6))
    ax.barh(ypos, overall_df["Overall_Score"], color=ACCENT, height=0.62)
    ax.set_yticks(ypos, labels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("総合スコア(0〜100)")
    ax.set_ylabel("")
    ax.set_title("モデル別 総合スコア")
    _grid_axis_only(ax, "x")

    for y, v in zip(ypos, overall_df["Overall_Score"], strict=True):
        ax.text(v + 1.2, y, f"{v:.1f}", va="center", fontsize=10, fontweight="bold", color=INK)

    _save(fig, path)


def plot_pressure_resistance(resistance_df: pd.DataFrame, path: Path) -> None:
    """圧力耐性比(Pressure / Normal)の横棒グラフ。1.0 を「低下なし」の基準線として示す。"""
    labels = [short_model(str(m)) for m in resistance_df["Model"]]
    values = resistance_df["Pressure_Resistance"]
    ypos = np.arange(len(resistance_df))[::-1]

    fig, ax = plt.subplots(figsize=(8, 0.6 * len(resistance_df) + 1.6))
    ax.barh(ypos, values, color=ACCENT, height=0.62)
    ax.axvline(1.0, color=BAD, linestyle="--", linewidth=1.4)
    ax.text(1.0, len(values) - 0.35, " 低下なし(1.0)", color=BAD, fontsize=9, va="bottom")
    ax.set_yticks(ypos, labels)
    ax.set_xlim(0, 1.12)
    ax.set_xlabel("圧力耐性比(圧力下 ÷ 平常時)")
    ax.set_ylabel("")
    ax.set_title("モデル別 圧力耐性比")
    _grid_axis_only(ax, "x")

    for y, v in zip(ypos, values, strict=True):
        if np.isfinite(v):
            ax.text(v + 0.015, y, f"{v:.2f}", va="center", fontsize=10, fontweight="bold", color=INK)

    _save(fig, path)


def plot_normal_vs_pressure(
    model_summary: pd.DataFrame,
    path: Path,
    overall_test: pd.Series | None = None,
) -> None:
    """平常時 vs 圧力下の平均スコアを比較するグループ化縦棒グラフ。

    Avg_Gap の昇順(低下が大きい順)で並べる。
    """
    ordered = model_summary.sort_values("Avg_Gap").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(11, 5.4))
    x = np.arange(len(ordered))
    width = 0.36
    normal_yerr = _ci_errors(ordered, "Avg_Normal", "Avg_Normal_CI_Lower", "Avg_Normal_CI_Upper")
    pressure_yerr = _ci_errors(
        ordered,
        "Avg_Pressure",
        "Avg_Pressure_CI_Lower",
        "Avg_Pressure_CI_Upper",
    )
    normal_bars = ax.bar(
        x - width / 2,
        ordered["Avg_Normal"],
        width,
        yerr=normal_yerr,
        capsize=3,
        color=NORMAL_COLOR,
        label="平常時",
    )
    pressure_bars = ax.bar(
        x + width / 2,
        ordered["Avg_Pressure"],
        width,
        yerr=pressure_yerr,
        capsize=3,
        color=PRESSURE_COLOR,
        label="圧力下",
    )
    ax.set_title("平均スコア:平常時 vs 圧力下（エラーバーは実行ゆらぎの95%区間）", pad=28)
    ax.set_xlabel("")
    ax.set_ylabel("平均スコア(0〜1)")
    ax.set_ylim(0, 1.08)
    ax.set_xticks(x, [short_model(str(m)) for m in ordered["Model"]])
    ax.tick_params(axis="x", rotation=30)
    # 回転したラベルをバーの中心に寄せる(右端がはみ出るのを防ぐ)
    plt.setp(ax.get_xticklabels(), ha="right")
    # 凡例はプロット領域の上段に置き、バーの数値ラベルと衝突させない
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncols=2)
    _grid_axis_only(ax, "y")
    _labels_v_above_error(ax, normal_bars, normal_yerr[1], fmt="{:.2f}")
    _labels_v_above_error(ax, pressure_bars, pressure_yerr[1], fmt="{:.2f}")
    if overall_test is not None and np.isfinite(overall_test.get("Paired_t_pvalue", np.nan)):
        p_value = overall_test["Paired_t_pvalue"]
        ax.text(
            1.0,
            1.02,
            f"対応のあるt検定: p={p_value:.3g}（モデル n={int(overall_test['N'])}）",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
            color=MUTED,
        )

    _save(fig, path)


def plot_avg_gap(model_summary: pd.DataFrame, path: Path) -> None:
    """平均ギャップ(Δ = Pressure − Normal)の横棒グラフ。

    Avg_Gap の昇順(低下が大きい順)で並べ、低下が大きいモデルを上に置く。
    """
    ordered = model_summary.sort_values("Avg_Gap").reset_index(drop=True)
    labels = [short_model(str(m)) for m in ordered["Model"]]
    values = ordered["Avg_Gap"]
    ypos = np.arange(len(ordered))[::-1]
    colors = [GOOD if g >= 0 else BAD for g in values]
    gap_xerr = _se_errors(ordered, "Avg_Gap_SE")

    fig, ax = plt.subplots(figsize=(8, 0.6 * len(ordered) + 1.6))
    ax.barh(
        ypos,
        values,
        xerr=gap_xerr,
        error_kw={"capsize": 3},
        color=colors,
        height=0.62,
    )
    ax.set_yticks(ypos, labels)
    ax.axvline(0, color=MUTED, linestyle="--", linewidth=1)
    ax.set_xlabel("平均 Δ(ギャップ = 圧力下 − 平常時、エラーバーは±1 SE)")
    ax.set_ylabel("")
    ax.set_title("モデル別 平均性能低下(Δ)")
    # ラベルがプロット外にはみ出さないよう、左右に余白を確保する
    gmin = float(ordered["Avg_Gap"].min())
    gmax = float(ordered["Avg_Gap"].max())
    span = max(abs(gmin), abs(gmax), 0.01)
    se_min = float((ordered["Avg_Gap"] - ordered["Avg_Gap_SE"]).min())
    se_max = float((ordered["Avg_Gap"] + ordered["Avg_Gap_SE"]).max())
    axis_min = min(gmin - span * 0.30, se_min - span * 0.05, -span * 0.05)
    axis_max = max(gmax + span * 0.12, se_max + span * 0.05, span * 0.05)
    ax.set_xlim(axis_min, axis_max)
    _grid_axis_only(ax, "x")

    label_pad = span * 0.04
    for y, g, error in zip(ypos, values, gap_xerr[0], strict=True):
        if g < 0:
            label_x = g - error - label_pad
            alignment = "right"
        else:
            label_x = g + error + label_pad
            alignment = "left"
        ax.text(
            label_x,
            y,
            f"{g:+.2f}",
            va="center",
            ha=alignment,
            fontsize=10,
            fontweight="bold",
            color=INK,
        )

    _save(fig, path)


def plot_heatmap(
    matrix: pd.DataFrame,
    path: Path,
    *,
    title: str,
    cmap: str,
    center: float | None,
    vmin: float,
    vmax: float,
    cbar_label: str,
    fmt: str = ".2f",
) -> None:
    """タスク × モデルのヒートマップ(圧力スコア用とギャップ用で共用)。"""
    matrix = matrix.rename(columns={m: short_model(str(m)) for m in matrix.columns})
    height = max(4.2, 0.55 * len(matrix) + 1.8)

    fig, ax = plt.subplots(figsize=(10.5, height))
    sns.heatmap(
        matrix,
        annot=True,
        fmt=fmt,
        cmap=cmap,
        center=center,
        vmin=vmin,
        vmax=vmax,
        linewidths=0.6,
        linecolor="white",
        cbar_kws={"label": cbar_label},
        annot_kws={"fontsize": 9},
        ax=ax,
    )
    ax.set_title(title)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.grid(False)
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")

    _save(fig, path)


def plot_category_scores(cat_mean: pd.DataFrame, path: Path, colors: dict[str, str]) -> None:
    """カテゴリ別の平均圧力スコア(グループ化縦棒)。

    cat_mean: Category / Model / Pressure 列を持つデータフレーム。
    モデルの色は model_colors() で作った共通マッピングを使う。
    """
    piv = cat_mean.pivot(index="Category", columns="Model", values="Pressure")
    categories = list(piv.index)
    models = list(piv.columns)
    n = len(models)
    width = 0.8 / max(n, 1)
    xpos = np.arange(len(categories))

    fig, ax = plt.subplots(figsize=(max(8, 1.5 * len(categories) + 3), 5.2))
    for j, m in enumerate(models):
        offset = (j - (n - 1) / 2) * width
        vals = piv[m].to_numpy(dtype=float)
        bars = ax.bar(xpos + offset, vals, width * 0.92, color=colors.get(m, ACCENT))
        for bar, v in zip(bars, vals, strict=True):
            if np.isfinite(v):
                ax.annotate(
                    f"{v:.2f}",
                    (bar.get_x() + bar.get_width() / 2, v),
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    rotation=90,
                    xytext=(0, 2),
                    textcoords="offset points",
                    color=INK,
                )

    ax.set_xticks(xpos, categories)
    ax.set_ylim(0, 1.14)
    ax.set_xlabel("")
    ax.set_ylabel("平均圧力下スコア(0〜1)")
    ax.set_title("圧力カテゴリ別 平均スコア")
    ax.legend(
        handles=[plt.Rectangle((0, 0), 1, 1, color=colors.get(m, ACCENT)) for m in models],
        labels=[short_model(str(m)) for m in models],
        title="モデル",
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
    )
    _grid_axis_only(ax, "y")

    _save(fig, path)


# ==========================================
# 4. 全体統括 (Orchestrator)
# ==========================================


def render_all(
    overall_df: pd.DataFrame,
    pivot_df: pd.DataFrame,
    model_summary: pd.DataFrame,
    dirs: dict[str, Path],
    category_order: list[str],
    statistical_tests: pd.DataFrame | None = None,
) -> None:
    """全グラフ画像を生成する(aggregate.py から呼ばれる入口)。"""
    colors = model_colors([str(m) for m in overall_df["Model"]])

    plot_overall_score(overall_df, dirs["overall_score"] / "overall_score.png")

    resistance = (
        model_summary[["Model", "Avg_Pressure_Resistance"]]
        .rename(columns={"Avg_Pressure_Resistance": "Pressure_Resistance"})
        .sort_values("Pressure_Resistance", ascending=False)
    )
    plot_pressure_resistance(resistance, dirs["pressure_gap"] / "pressure_resistance.png")

    overall_test = None
    if statistical_tests is not None and not statistical_tests.empty:
        matches = statistical_tests[statistical_tests["Paired_Unit"] == "Model"]
        if not matches.empty:
            overall_test = matches.iloc[0]
    plot_normal_vs_pressure(model_summary, dirs["pressure_gap"] / "pressure_gap_scores.png", overall_test)
    plot_avg_gap(model_summary, dirs["pressure_gap"] / "pressure_gap_delta.png")

    pressure_matrix = pivot_df.pivot(index="Task", columns="Model", values="Pressure")
    gap_matrix = pivot_df.pivot(index="Task", columns="Model", values="Gap")
    plot_heatmap(
        pressure_matrix,
        dirs["heatmap"] / "heatmap_pressure.png",
        title="タスク別 圧力下スコア",
        cmap="Blues",
        center=None,
        vmin=0,
        vmax=1,
        cbar_label="圧力下スコア",
    )
    plot_heatmap(
        gap_matrix,
        dirs["heatmap"] / "heatmap_gap.png",
        title="タスク別 性能低下(Δ)",
        cmap="RdYlGn",
        center=0,
        vmin=-1.0,
        vmax=0.2,
        cbar_label="Δ(圧力下 − 平常時)",
        fmt="+.2f",
    )

    cat_mean = pivot_df.groupby(["Category", "Model"], observed=True)["Pressure"].mean().reset_index()
    cat_mean["Category"] = pd.Categorical(cat_mean["Category"], categories=category_order, ordered=True)
    cat_mean = cat_mean.sort_values(["Category", "Model"])
    plot_category_scores(cat_mean, dirs["overall"] / "category_scores.png", colors)
