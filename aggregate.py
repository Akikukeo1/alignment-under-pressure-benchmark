"""AUPB の集計スクリプト。

Kaggle Benchmark のリーダーボードCSVを読み込み、results/ 以下に
CSV とグラフ画像を生成する。

    - データ処理と CSV 出力はこのファイルが担当
    - グラフ描画は charts.py へ委譲(charts.render_all)

使い方:
    uv run aggregate.py [-c config.toml]
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import charts

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# カテゴリの表示順(CSV・グラフともにこの順で固定)
CATEGORY_ORDER = ["Bias", "Ethics", "Logic", "Robustness", "Safety"]


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
    """tasks/ ディレクトリ内の TOML ファイルからタスクのメタデータ(Category, Difficulty 等)を読み込みます。"""
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
# 3. CSV 出力 (CSV Writers)
# ==========================================

def write_csvs(overall_df: pd.DataFrame, pivot_df: pd.DataFrame, dirs: dict[str, Path]) -> pd.DataFrame:
    """results/ 以下のすべての CSV を書き出し、モデル別サマリーを返します。"""
    overall_df.to_csv(dirs["overall_score"] / "overall_score.csv", index=False, encoding="utf-8-sig")

    gap_by_task = pivot_df.sort_values(by=["Task", "Model"]).reset_index(drop=True)
    gap_by_task.to_csv(dirs["pressure_gap"] / "pressure_gap_by_task.csv", index=False, encoding="utf-8-sig")

    model_summary = _calculate_model_summary(pivot_df, overall_df)
    model_summary.to_csv(
        dirs["pressure_gap"] / "pressure_gap_by_model.csv", index=False, encoding="utf-8-sig"
    )

    pr_df = model_summary[["Model", "Avg_Pressure_Resistance"]].rename(
        columns={"Avg_Pressure_Resistance": "Pressure_Resistance"}
    )
    pr_df.to_csv(dirs["pressure_gap"] / "pressure_resistance.csv", index=False, encoding="utf-8-sig")

    pivot_df.pivot(index="Task", columns="Model", values="Pressure").to_csv(
        dirs["heatmap"] / "heatmap_pressure.csv", encoding="utf-8-sig"
    )
    pivot_df.pivot(index="Task", columns="Model", values="Gap").to_csv(
        dirs["heatmap"] / "heatmap_gap.csv", encoding="utf-8-sig"
    )

    cat_summary = (
        pivot_df.groupby(["Category", "Model"])["Pressure"]
        .mean()
        .unstack(level="Model")
        .reset_index()
    )
    cat_summary.to_csv(dirs["overall"] / "category_scores.csv", index=False, encoding="utf-8-sig")

    overall_summary = model_summary.rename(
        columns={
            "Overall_Score": "Overall Score",
            "Avg_Normal": "Avg Normal",
            "Avg_Pressure": "Avg Pressure",
            "Avg_Gap": "Avg Δ (Gap)",
            "Avg_Pressure_Resistance": "Pressure Resistance Ratio",
        }
    )
    overall_summary.to_csv(dirs["overall"] / "overall_summary.csv", index=False, encoding="utf-8-sig")

    return model_summary


# ==========================================
# 4. 全体統括関数 (Main Orchestrator)
# ==========================================

def analyze_and_output(overall_df: pd.DataFrame, pivot_df: pd.DataFrame, output_dir: str) -> None:
    """CSV 出力 → グラフ描画の順に処理を統括します。"""
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

    # CSV 出力(モデル別サマリーはグラフ側でも使う)
    model_summary = write_csvs(overall_df, pivot_df, dirs)

    # グラフ描画(charts.py へ委譲)
    charts.render_all(overall_df, pivot_df, model_summary, dirs, CATEGORY_ORDER)

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

    # 描画スタイルの適用
    charts.setup_style()

    # 分析 & 出力
    analyze_and_output(overall_df, pivot_df, output_dir)


if __name__ == "__main__":
    main()
