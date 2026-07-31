import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# グラフ描画のスタイル設定
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Meiryo", "TakaoPGothic"]
plt.rcParams["axes.unicode_minus"] = False


# ==========================================
# 1. 設定 & メタデータ読み込み (Config & Metadata Loader)
# ==========================================

def load_config(config_path: str) -> dict:
    """TOML設定ファイルを読み込みます。"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data.get("aggregate", {})


def load_task_metadata(tasks_dir: str) -> dict:
    """tasks/ ディレクトリ内の TOML ファイルからタスクのメタデータ（Category, Difficulty 等）を読み込みます。"""
    tasks_path = Path(tasks_dir)
    metadata = {}
    if not tasks_path.exists():
        return metadata

    for file in tasks_path.glob("*.toml"):
        try:
            with open(file, "rb") as f:
                task_data = tomllib.load(f).get("task", {})
                name = task_data.get("name")
                if name:
                    metadata[name] = {
                        "category": task_data.get("category", "Unknown"),
                        "difficulty": task_data.get("difficulty", "Unknown"),
                        "filename": file.stem,
                    }
        except Exception as e:
            print(f"Warning: {file} の読み込みに失敗しました: {e}")

    return metadata


# ==========================================
# 2. データ処理関数 (Data Processing)
# ==========================================

def parse_csv_data(csv_path: str, task_metadata: dict):
    """CSVをパースし、総合スコアとタスク別スコアのデータフレームに整形します。"""
    df = pd.read_csv(csv_path)

    # NaN や空文字の処理
    df["Task_Name"] = df["Task_Name"].fillna("").astype(str).str.strip()
    df["Model"] = df["Model"].astype(str).str.strip()

    overall_df = _extract_overall_scores(df)
    pivot_df = _extract_task_scores(df, task_metadata)

    return overall_df, pivot_df


def _extract_overall_scores(df: pd.DataFrame) -> pd.DataFrame:
    """総合スコアの抽出 (Task_Name が空の行)"""
    return (
        df[df["Task_Name"] == ""][["Model", "Numerical_Result", "Evaluation_Date"]]
        .rename(columns={"Numerical_Result": "Overall_Score"})
        .sort_values(by="Overall_Score", ascending=False)
        .reset_index(drop=True)
    )


def _extract_task_scores(df: pd.DataFrame, task_metadata: dict) -> pd.DataFrame:
    """タスク別スコアの計算とピボット処理"""
    task_rows = df[df["Task_Name"] != ""].copy()
    records = []

    for _, row in task_rows.iterrows():
        raw_name = row["Task_Name"]
        model = row["Model"]
        result = float(row["Numerical_Result"])

        # removeprefix を使用して接頭辞を削除
        if raw_name.startswith("AUPB_Normal_"):
            task_base = raw_name.removeprefix("AUPB_Normal_")
            condition = "Normal"
        elif raw_name.startswith("AUPB_"):
            task_base = raw_name.removeprefix("AUPB_")
            condition = "Pressure"
        else:
            task_base = raw_name
            condition = "Pressure"

        meta = task_metadata.get(task_base, {"category": "Other", "difficulty": "Unknown"})
        records.append({
            "Model": model,
            "Task": task_base,
            "Category": meta["category"],
            "Difficulty": meta["difficulty"],
            "Condition": condition,
            "Score": result,
        })

    records_df = pd.DataFrame(records)

    # Normal と Pressure をピボットして1行にまとめる
    pivot_df = records_df.pivot(
        index=["Model", "Task", "Category", "Difficulty"],
        columns="Condition",
        values="Score",
    ).reset_index()

    # もし片方の条件が存在しない場合は NaN
    if "Normal" not in pivot_df.columns:
        pivot_df["Normal"] = np.nan
    if "Pressure" not in pivot_df.columns:
        pivot_df["Pressure"] = np.nan

    # Δ (Gap) = Pressure - Normal
    pivot_df["Gap"] = pivot_df["Pressure"] - pivot_df["Normal"]

    # Pressure Resistance = Pressure / Normal
    pivot_df["Pressure_Resistance"] = np.where(
        pivot_df["Normal"] > 0,
        pivot_df["Pressure"] / pivot_df["Normal"],
        np.where(pivot_df["Pressure"] == 0, 1.0, np.nan),
    )

    return pivot_df


def _calculate_model_summary(pivot_df: pd.DataFrame, overall_df: pd.DataFrame) -> pd.DataFrame:
    """モデルごとの平均指標を算出します。"""
    summary = (
        pivot_df.groupby("Model")
        .agg(
            Avg_Normal=("Normal", "mean"),
            Avg_Pressure=("Pressure", "mean"),
            Avg_Gap=("Gap", "mean"),
            Avg_Pressure_Resistance=("Pressure_Resistance", "mean"),
        )
        .reset_index()
    )
    summary = pd.merge(summary, overall_df[["Model", "Overall_Score"]], on="Model", how="left")
    return summary.sort_values(by="Avg_Gap", ascending=False).reset_index(drop=True)


# ==========================================
# 3. 描画用ヘルパー (Plotting Utilities)
# ==========================================

def _add_bar_labels_horizontal(ax, fmt="{:.1f}", offset=0.5):
    """横棒グラフに数値を書き込む共通処理"""
    for bar in ax.patches:
        w = bar.get_width()
        if w is not None and np.isfinite(w) and w != 0:
            ax.text(
                w + offset,
                bar.get_y() + bar.get_height() / 2,
                fmt.format(w),
                va="center",
                fontsize=10,
                fontweight="bold",
            )


def _add_bar_labels_vertical(ax, fmt="{:.2f}", offset_points=2):
    """縦棒グラフに数値を書き込む共通処理"""
    for bar in ax.patches:
        h = bar.get_height()
        if h is not None and np.isfinite(h) and h > 0:
            ax.annotate(
                fmt.format(h),
                (bar.get_x() + bar.get_width() / 2.0, h),
                ha="center",
                va="bottom",
                fontsize=9,
                xytext=(0, offset_points),
                textcoords="offset points",
            )


# ==========================================
# 4. 各出力ごとの個別関数 (Output Handlers)
# ==========================================

def plot_overall_score(overall_df: pd.DataFrame, save_dir: Path):
    """1. モデル別総合性能 (Overall Score) のプロットとCSV出力"""
    overall_csv = save_dir / "overall_score.csv"
    overall_df.to_csv(overall_csv, index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(8, 5))
    palette_colors = sns.color_palette("viridis", len(overall_df))
    palette_dict = dict(zip(overall_df["Model"], palette_colors))

    sns.barplot(
        data=overall_df,
        x="Overall_Score",
        y="Model",
        palette=palette_dict,
        ax=ax,
        hue="Model",
        legend=False,
    )
    ax.set_title("1. Overall Score by Model", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Overall Score", fontsize=12)
    ax.set_ylabel("Model", fontsize=12)

    _add_bar_labels_horizontal(ax, fmt="{:.1f}", offset=0.5)
    ax.set_xlim(0, max(100, overall_df["Overall_Score"].max() + 10))

    fig.savefig(save_dir / "overall_score.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_pressure_gap(pivot_df: pd.DataFrame, overall_df: pd.DataFrame, save_dir: Path):
    """2. Pressure による性能低下 (Pressure Gap & Resistance) の出力"""
    # タスクごとの Gap
    gap_by_task = pivot_df.sort_values(by=["Task", "Model"]).reset_index(drop=True)
    gap_by_task.to_csv(save_dir / "pressure_gap_by_task.csv", index=False, encoding="utf-8-sig")

    # モデルごとの集計
    model_summary = _calculate_model_summary(pivot_df, overall_df)
    model_summary.to_csv(save_dir / "pressure_gap_by_model.csv", index=False, encoding="utf-8-sig")

    # Pressure Resistance CSV
    pr_df = model_summary[["Model", "Avg_Pressure_Resistance"]].rename(
        columns={"Avg_Pressure_Resistance": "Pressure_Resistance"}
    )
    pr_df.to_csv(save_dir / "pressure_resistance.csv", index=False, encoding="utf-8-sig")

    # 画像: Pressure Gap
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 左ペイン: Normal vs Pressure
    m_melted = pd.melt(
        model_summary,
        id_vars=["Model"],
        value_vars=["Avg_Normal", "Avg_Pressure"],
        var_name="Condition",
        value_name="Score",
    )
    m_melted["Condition"] = m_melted["Condition"].map({"Avg_Normal": "Normal", "Avg_Pressure": "Pressure"})

    sns.barplot(
        data=m_melted,
        x="Model",
        y="Score",
        hue="Condition",
        palette={"Normal": "#4C72B0", "Pressure": "#C44E52"},
        ax=ax1,
    )
    ax1.set_title("Average Score: Normal vs Pressure", fontsize=13, fontweight="bold")
    ax1.set_ylabel("Average Score (0.0 - 1.0)", fontsize=11)
    ax1.set_ylim(0, 1.1)
    ax1.tick_params(axis="x", rotation=30)
    _add_bar_labels_vertical(ax1, fmt="{:.2f}")

    # 右ペイン: 平均 Δ (Gap)
    colors = ["#2ca02c" if g >= 0 else "#d62728" for g in model_summary["Avg_Gap"]]
    color_dict = dict(zip(model_summary["Model"], colors))

    sns.barplot(
        data=model_summary,
        x="Avg_Gap",
        y="Model",
        palette=color_dict,
        ax=ax2,
        hue="Model",
        legend=False,
    )
    ax2.axvline(0, color="gray", linestyle="--", linewidth=1)
    ax2.set_title("Average Performance Drop (Δ = Pressure - Normal)", fontsize=13, fontweight="bold")
    ax2.set_xlabel("Average Δ", fontsize=11)

    for bar in ax2.patches:
        w = bar.get_width()
        if w is not None and np.isfinite(w) and abs(w) > 0:
            offset = 0.02 if w >= 0 else -0.05
            ax2.text(
                w + offset,
                bar.get_y() + bar.get_height() / 2,
                f"{w:+.2f}",
                va="center",
                fontsize=10,
                fontweight="bold",
            )

    fig.savefig(save_dir / "pressure_gap.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # 画像: Pressure Resistance
    fig, ax = plt.subplots(figsize=(8, 5))
    pr_sorted = pr_df.sort_values(by="Pressure_Resistance", ascending=False)
    sns.barplot(
        data=pr_sorted,
        x="Pressure_Resistance",
        y="Model",
        palette="crest",
        ax=ax,
        hue="Model",
        legend=False,
    )
    ax.axvline(1.0, color="red", linestyle="--", linewidth=1.5, label="No Drop (1.0)")
    ax.set_title("Pressure Resistance Ratio (Pressure / Normal)", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Pressure Resistance Index", fontsize=12)
    ax.set_ylabel("Model", fontsize=12)
    ax.legend(loc="lower right")

    _add_bar_labels_horizontal(ax, fmt="{:.2f}", offset=0.02)
    ax.set_xlim(0, max(1.2, pr_sorted["Pressure_Resistance"].max() + 0.15))

    fig.savefig(save_dir / "pressure_resistance.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_heatmaps(pivot_df: pd.DataFrame, save_dir: Path):
    """3. タスクごとの弱点 (Heatmap) のプロットと保存"""
    # Pressure Score Matrix
    pressure_matrix = pivot_df.pivot(index="Task", columns="Model", values="Pressure")
    pressure_matrix.to_csv(save_dir / "heatmap_pressure.csv", encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(
        pressure_matrix,
        annot=True,
        fmt=".2f",
        cmap="YlGnBu",
        cbar_kws={"label": "Pressure Score"},
        ax=ax,
        linewidths=0.5,
        vmin=0,
        vmax=1,
    )
    ax.set_title("3. Task-level Performance under Pressure (Heatmap)", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Task", fontsize=12)
    plt.xticks(rotation=30, ha="right")

    fig.savefig(save_dir / "heatmap_pressure.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Gap (Δ) Matrix
    gap_matrix = pivot_df.pivot(index="Task", columns="Model", values="Gap")
    gap_matrix.to_csv(save_dir / "heatmap_gap.csv", encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(
        gap_matrix,
        annot=True,
        fmt="+.2f",
        cmap="RdYlGn",
        center=0,
        cbar_kws={"label": "Δ (Pressure - Normal)"},
        ax=ax,
        linewidths=0.5,
        vmin=-1.0,
        vmax=0.2,
    )
    ax.set_title("Task-level Performance Drop Δ (Heatmap)", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Task", fontsize=12)
    plt.xticks(rotation=30, ha="right")

    fig.savefig(save_dir / "heatmap_gap.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_category_scores(pivot_df: pd.DataFrame, save_dir: Path):
    """4. 圧力の種類ごとの分析 (Category Analysis) のプロットとCSV出力"""
    cat_summary = (
        pivot_df.groupby(["Category", "Model"])["Pressure"]
        .mean()
        .unstack(level="Model")
        .reset_index()
    )
    cat_summary.to_csv(save_dir / "category_scores.csv", index=False, encoding="utf-8-sig")

    cat_melted = pivot_df.groupby(["Category", "Model"])["Pressure"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(
        data=cat_melted,
        x="Category",
        y="Pressure",
        hue="Model",
        palette="Set2",
        ax=ax,
    )
    ax.set_title("4. Performance by Pressure Category", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Pressure Category", fontsize=12)
    ax.set_ylabel("Average Pressure Score", fontsize=12)
    ax.set_ylim(0, 1.1)
    ax.legend(title="Model", bbox_to_anchor=(1.05, 1), loc="upper left")

    _add_bar_labels_vertical(ax, fmt="{:.2f}")

    fig.savefig(save_dir / "category_scores.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_overall_summary(pivot_df: pd.DataFrame, overall_df: pd.DataFrame, save_dir: Path):
    """5. Overall Summary (リーダーボード風のダッシュボード) のCSVとテーブル画像出力"""
    model_summary = _calculate_model_summary(pivot_df, overall_df)
    overall_summary = model_summary.rename(
        columns={
            "Overall_Score": "Overall Score",
            "Avg_Normal": "Avg Normal",
            "Avg_Pressure": "Avg Pressure",
            "Avg_Gap": "Avg Δ (Gap)",
            "Avg_Pressure_Resistance": "Pressure Resistance Ratio",
        }
    )
    overall_summary.to_csv(save_dir / "overall_summary.csv", index=False, encoding="utf-8-sig")

    # サマリー画像 (ダッシュボード的グラフ)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axis("off")
    ax.axis("tight")
    table_data = overall_summary.copy()

    for col in ["Avg Normal", "Avg Pressure", "Avg Δ (Gap)", "Pressure Resistance Ratio"]:
        table_data[col] = table_data[col].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else "N/A")
    table_data["Overall Score"] = table_data["Overall Score"].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "N/A")

    table = ax.table(
        cellText=table_data.values,
        colLabels=table_data.columns,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)

    # ヘッダーの装飾
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#40466e")
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
        else:
            if row % 2 == 0:
                cell.set_facecolor("#f1f1f2")

    ax.set_title("AUPB Overall Summary Metrics", fontsize=14, fontweight="bold", pad=20)
    fig.savefig(save_dir / "overall_summary.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ==========================================
# 5. 全体統括関数 (Main Orchestrator)
# ==========================================

def analyze_and_output(overall_df: pd.DataFrame, pivot_df: pd.DataFrame, output_dir: str):
    """全体の出力処理を統括（どの順番で何が実行されるかが一目でわかる）"""
    out_path = Path(output_dir)

    # 各ディレクトリのマッピング
    dirs = {
        "overall_score": out_path / "overall_score",
        "pressure_gap": out_path / "pressure_gap",
        "heatmap": out_path / "heatmap",
        "overall": out_path / "overall",
    }

    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # モジュール化された関数を順次実行
    plot_overall_score(overall_df, dirs["overall_score"])
    plot_pressure_gap(pivot_df, overall_df, dirs["pressure_gap"])
    plot_heatmaps(pivot_df, dirs["heatmap"])
    plot_category_scores(pivot_df, dirs["overall"])
    plot_overall_summary(pivot_df, overall_df, dirs["overall"])

    print(f"分析完了! 結果は '{output_dir}/' ディレクトリに出力されました:")
    for k, v in dirs.items():
        print(f" - [{k}]: {v}")


def main():
    parser = argparse.ArgumentParser(description="AUPB CSV分析および視覚化ツール")
    parser.add_argument(
        "--config",
        "-c",
        default="config.toml",
        help="設定ファイル(TOML)のパス (デフォルト: config.toml)",
    )
    args = parser.parse_args()

    # 設定読み込み
    cfg = load_config(args.config)
    csv_path = cfg.get("input_csv", "akikukeo1_alignment-under-pressure-benchmark_leaderboard.csv")
    output_dir = cfg.get("output_dir", "results")
    tasks_dir = cfg.get("tasks_dir", "tasks")

    print(f"設定ファイルを読み込みました: {args.config}")
    print(f" - 入力CSV: {csv_path}")
    print(f" - タスク定義: {tasks_dir}")
    print(f" - 出力先: {output_dir}")

    # メタデータ読み込み
    metadata = load_task_metadata(tasks_dir)

    # CSV パース
    overall_df, pivot_df = parse_csv_data(csv_path, metadata)

    # 分析 & 出力
    analyze_and_output(overall_df, pivot_df, output_dir)


if __name__ == "__main__":
    main()
