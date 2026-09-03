"""AUPB の集計スクリプト。

Kaggle Benchmark のリーダーボードCSVを読み込み、results/ 以下に
CSV とグラフ画像を生成する。

    - データ処理と CSV 出力はこのファイルが担当
    - グラフ描画は charts.py へ委譲(charts.render_all)

使い方:
    uv run aggregate.py [-c config.toml]
"""

import argparse
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import charts
from analysis_stats import paired_summary, proportion_stats, sampling_summary

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


def load_scoring_config(config_path: str) -> tuple[dict[str, int], str]:
    """不確実性計算に必要な難易度別試行回数と採点方式を読み込みます。"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    with open(path, "rb") as f:
        data = tomllib.load(f)

    loops = {
        str(difficulty): int(count)
        for difficulty, count in data.get("loops", {}).items()
        if int(count) > 0
    }
    method = str(data.get("scoring", {}).get("method", "custom"))
    return loops, method


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


def parse_csv_data(
    csv_path: str,
    task_metadata: dict,
    loop_counts: dict[str, int] | None = None,
    scoring_method: str = "custom",
):
    """CSVをパースし、総合スコアとタスク別スコアのデータフレームに整形します。"""
    df = pd.read_csv(csv_path)

    # NaN や空文字の処理
    df["Task_Name"] = df["Task_Name"].fillna("").astype(str).str.strip()
    df["Model"] = df["Model"].astype(str).str.strip()

    overall_df = _extract_overall_scores(df)
    pivot_df = _extract_task_scores(df, task_metadata, loop_counts, scoring_method)

    return overall_df, pivot_df


def _extract_overall_scores(df: pd.DataFrame) -> pd.DataFrame:
    """総合スコアの抽出 (Task_Name が空の行)"""
    return (
        df[df["Task_Name"] == ""][["Model", "Numerical_Result", "Evaluation_Date"]]
        .rename(columns={"Numerical_Result": "Overall_Score"})
        .sort_values(by="Overall_Score", ascending=False)
        .reset_index(drop=True)
    )


def _validate_task_scores(records_df: pd.DataFrame, task_metadata: dict) -> None:
    """タスク別得点の品質検証(欠損・範囲・重複・タスク網羅)。

    旧 paper_figures.load_scores() にあった検証を唯一の集計器である本ファイルへ
    移設したもの。タスク網羅チェックはハードコードではなく tasks/*.toml の
    タスク定義数と照合するため、タスク追加時の改修箇所はここだけでよい。
    """
    if records_df["Score"].isna().any():
        bad = records_df.loc[records_df["Score"].isna(), ["Model", "Task"]]
        raise ValueError(f"タスクの得点に欠損があります:\n{bad.to_string(index=False)}")

    out_of_range = ~records_df["Score"].between(0, 1)
    if out_of_range.any():
        bad = records_df.loc[out_of_range, ["Model", "Task"]]
        raise ValueError(f"0点から1点の範囲外にあるタスク得点があります:\n{bad.to_string(index=False)}")

    dup_mask = records_df.duplicated(["Model", "Task", "Condition"])
    if dup_mask.any():
        bad = records_df.loc[dup_mask, ["Model", "Task", "Condition"]]
        raise ValueError(f"同じモデル・タスク・条件の行が重複しています:\n{bad.to_string(index=False)}")

    # タスク網羅: 各モデル×条件で、タスク定義(TOML)とまったく同じタスク集合を持つこと
    expected_tasks = set(task_metadata.keys())
    if not expected_tasks:
        print("Warning: タスク定義(tasks/*.toml)が読めないため、タスク網羅チェックをスキップします")
        return
    coverage = records_df.groupby(["Model", "Condition"])["Task"].agg(set)
    for (model, condition), actual in coverage.items():
        missing = sorted(expected_tasks - actual)
        unknown = sorted(actual - expected_tasks)
        if missing:
            raise ValueError(f"{model}({condition}): タスク定義に対して欠落しているタスクがあります: {missing}")
        if unknown:
            raise ValueError(f"{model}({condition}): タスク定義(TOML)に存在しないタスクがあります: {unknown}")


def _extract_task_scores(
    df: pd.DataFrame,
    task_metadata: dict,
    loop_counts: dict[str, int] | None = None,
    scoring_method: str = "custom",
) -> pd.DataFrame:
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
        record = {
            "Model": model,
            "Task": task_base,
            "Category": meta["category"],
            "Difficulty": meta["difficulty"],
            "Condition": condition,
            "Score": result,
        }

        # linear スコアなら、リーダーボードに残っていない合格数を復元して
        # 二項分布に基づく試行単位の不確実性を計算できる。
        trials = None
        if scoring_method == "linear" and loop_counts is not None:
            trials = loop_counts.get(meta["difficulty"])
        uncertainty = proportion_stats(result, trials)
        record.update(uncertainty)
        records.append(record)

    records_df = pd.DataFrame(records)

    # 品質検証(欠損・0〜1 範囲・重複・タスク網羅)。失敗時はここで異常終了する
    _validate_task_scores(records_df, task_metadata)

    # Normal と Pressure のスコアをピボットして1行にまとめる
    index_columns = ["Model", "Task", "Category", "Difficulty"]
    pivot_df = records_df.pivot(
        index=index_columns,
        columns="Condition",
        values="Score",
    ).reset_index()

    # 試行単位の不確実性も同じキーでピボットして保持する。
    for statistic in ["Passes", "Trials", "SE", "CI_Lower", "CI_Upper"]:
        uncertainty_df = records_df.pivot(
            index=index_columns,
            columns="Condition",
            values=statistic,
        ).reset_index()
        uncertainty_df = uncertainty_df.rename(
            columns={condition: f"{condition}_{statistic}" for condition in ["Normal", "Pressure"]}
        )
        pivot_df = pivot_df.merge(uncertainty_df, on=index_columns, how="left")

    # もし片方の条件が存在しない場合は NaN
    if "Normal" not in pivot_df.columns:
        pivot_df["Normal"] = np.nan
    if "Pressure" not in pivot_df.columns:
        pivot_df["Pressure"] = np.nan

    # Δ (Gap) = Pressure - Normal
    pivot_df["Gap"] = pivot_df["Pressure"] - pivot_df["Normal"]
    pivot_df["Gap_SE"] = np.sqrt(pivot_df["Normal_SE"] ** 2 + pivot_df["Pressure_SE"] ** 2)
    # 条件間を独立とみなした保守的な差の区間。通常条件の上限と圧力条件の
    # 下限を組み合わせることで、個別タスクの不確実性を過小評価しない。
    pivot_df["Gap_CI_Lower"] = pivot_df["Pressure_CI_Lower"] - pivot_df["Normal_CI_Upper"]
    pivot_df["Gap_CI_Upper"] = pivot_df["Pressure_CI_Upper"] - pivot_df["Normal_CI_Lower"]

    # Pressure Resistance = Pressure / Normal
    pivot_df["Pressure_Resistance"] = np.where(
        pivot_df["Normal"] > 0,
        pivot_df["Pressure"] / pivot_df["Normal"],
        np.where(pivot_df["Pressure"] == 0, 1.0, np.nan),
    )

    return pivot_df


def _calculate_model_summary(pivot_df: pd.DataFrame, overall_df: pd.DataFrame) -> pd.DataFrame:
    """モデルごとの平均指標と不確実性、対応のある検定結果を算出します。"""
    summary = (
        pivot_df
        .groupby("Model")
        .agg(
            Avg_Normal=("Normal", "mean"),
            Avg_Pressure=("Pressure", "mean"),
            Avg_Gap=("Gap", "mean"),
            Avg_Pressure_Resistance=("Pressure_Resistance", "mean"),
        )
        .reset_index()
    )
    statistical_rows = []
    for model, group in pivot_df.groupby("Model", sort=False):
        stats = paired_summary(group["Normal"].tolist(), group["Pressure"].tolist())
        sampling = sampling_summary(
            group["Normal_Passes"].tolist(),
            group["Normal_Trials"].tolist(),
            group["Pressure_Passes"].tolist(),
            group["Pressure_Trials"].tolist(),
        )
        statistical_rows.append({
            "Model": model,
            "N_Paired_Tasks": stats["N"],
            "N_Sampling_Tasks": sampling["N"],
            # 図のエラーバーはタスク間のばらつきではなく、実行回数由来の区間を使う。
            "Avg_Normal_SE": sampling["Normal_SE"],
            "Avg_Normal_CI_Lower": sampling["Normal_CI_Lower"],
            "Avg_Normal_CI_Upper": sampling["Normal_CI_Upper"],
            "Avg_Pressure_SE": sampling["Pressure_SE"],
            "Avg_Pressure_CI_Lower": sampling["Pressure_CI_Lower"],
            "Avg_Pressure_CI_Upper": sampling["Pressure_CI_Upper"],
            "Avg_Gap_SE": sampling["Gap_SE"],
            "Avg_Gap_CI_Lower": sampling["Gap_CI_Lower"],
            "Avg_Gap_CI_Upper": sampling["Gap_CI_Upper"],
            # 検定は従来どおり、8タスクを対応単位にしたタスク差で行う。
            "Paired_t": stats["Paired_t"],
            "Paired_t_df": stats["Paired_t_df"],
            "Paired_t_pvalue": stats["Paired_t_pvalue"],
            "Wilcoxon_W": stats["Wilcoxon_W"],
            "Wilcoxon_N": stats["Wilcoxon_N"],
            "Wilcoxon_pvalue": stats["Wilcoxon_pvalue"],
        })
    statistical_df = pd.DataFrame(statistical_rows)
    summary = pd.merge(summary, statistical_df, on="Model", how="left")
    summary = pd.merge(summary, overall_df[["Model", "Overall_Score"]], on="Model", how="left")
    return summary.sort_values(by="Avg_Gap", ascending=False).reset_index(drop=True)


def _calculate_task_summary(pivot_df: pd.DataFrame) -> pd.DataFrame:
    """タスクごとの平均値、95% CI、対応のある検定結果を算出します。"""
    rows = []
    for (task, category, difficulty), group in pivot_df.groupby(
        ["Task", "Category", "Difficulty"], sort=False, observed=True
    ):
        stats = paired_summary(group["Normal"].tolist(), group["Pressure"].tolist())
        sampling = sampling_summary(
            group["Normal_Passes"].tolist(),
            group["Normal_Trials"].tolist(),
            group["Pressure_Passes"].tolist(),
            group["Pressure_Trials"].tolist(),
        )
        rows.append({
            "Task": task,
            "Category": category,
            "Difficulty": difficulty,
            "N_Models": stats["N"],
            "N_Sampling_Models": sampling["N"],
            "Avg_Normal": stats["Normal_Mean"],
            # 図の区間はモデル間のばらつきではなく、各モデルの試行ゆらぎを
            # タスク平均へ伝播したものに統一する。
            "Avg_Normal_SE": sampling["Normal_SE"],
            "Avg_Normal_CI_Lower": sampling["Normal_CI_Lower"],
            "Avg_Normal_CI_Upper": sampling["Normal_CI_Upper"],
            "Avg_Pressure": stats["Pressure_Mean"],
            "Avg_Pressure_SE": sampling["Pressure_SE"],
            "Avg_Pressure_CI_Lower": sampling["Pressure_CI_Lower"],
            "Avg_Pressure_CI_Upper": sampling["Pressure_CI_Upper"],
            "Avg_Gap": stats["Gap_Mean"],
            "Avg_Gap_SE": sampling["Gap_SE"],
            "Avg_Gap_CI_Lower": sampling["Gap_CI_Lower"],
            "Avg_Gap_CI_Upper": sampling["Gap_CI_Upper"],
            # モデル間の記述統計もCSVに残し、検定の単位と区間の意味を分ける。
            "Avg_Normal_Model_SE": stats["Normal_SE"],
            "Avg_Normal_Model_CI_Lower": stats["Normal_CI_Lower"],
            "Avg_Normal_Model_CI_Upper": stats["Normal_CI_Upper"],
            "Avg_Pressure_Model_SE": stats["Pressure_SE"],
            "Avg_Pressure_Model_CI_Lower": stats["Pressure_CI_Lower"],
            "Avg_Pressure_Model_CI_Upper": stats["Pressure_CI_Upper"],
            "Avg_Gap_Model_SE": stats["Gap_SE"],
            "Avg_Gap_Model_CI_Lower": stats["Gap_CI_Lower"],
            "Avg_Gap_Model_CI_Upper": stats["Gap_CI_Upper"],
            "Paired_t": stats["Paired_t"],
            "Paired_t_df": stats["Paired_t_df"],
            "Paired_t_pvalue": stats["Paired_t_pvalue"],
            "Wilcoxon_W": stats["Wilcoxon_W"],
            "Wilcoxon_N": stats["Wilcoxon_N"],
            "Wilcoxon_pvalue": stats["Wilcoxon_pvalue"],
        })
    return pd.DataFrame(rows).sort_values("Task").reset_index(drop=True)


def _test_record(comparison: str, paired_unit: str, stats: dict[str, float]) -> dict:
    """共通の統計的検定CSV行を作ります。"""
    return {
        "Comparison": comparison,
        "Paired_Unit": paired_unit,
        "N": stats["N"],
        "Mean_Normal": stats["Normal_Mean"],
        "SE_Normal": stats["Normal_SE"],
        "Normal_CI_Lower": stats["Normal_CI_Lower"],
        "Normal_CI_Upper": stats["Normal_CI_Upper"],
        "Mean_Pressure": stats["Pressure_Mean"],
        "SE_Pressure": stats["Pressure_SE"],
        "Pressure_CI_Lower": stats["Pressure_CI_Lower"],
        "Pressure_CI_Upper": stats["Pressure_CI_Upper"],
        "Mean_Gap": stats["Gap_Mean"],
        "SE_Gap": stats["Gap_SE"],
        "Gap_CI_Lower": stats["Gap_CI_Lower"],
        "Gap_CI_Upper": stats["Gap_CI_Upper"],
        "Paired_t": stats["Paired_t"],
        "Paired_t_df": stats["Paired_t_df"],
        "Paired_t_pvalue": stats["Paired_t_pvalue"],
        "Wilcoxon_W": stats["Wilcoxon_W"],
        "Wilcoxon_N": stats["Wilcoxon_N"],
        "Wilcoxon_pvalue": stats["Wilcoxon_pvalue"],
    }


def _calculate_statistical_tests(model_summary: pd.DataFrame, task_summary: pd.DataFrame) -> pd.DataFrame:
    """モデル単位とタスク単位の2種類の全体検定をまとめます。"""
    model_stats = paired_summary(model_summary["Avg_Normal"].tolist(), model_summary["Avg_Pressure"].tolist())
    task_stats = paired_summary(task_summary["Avg_Normal"].tolist(), task_summary["Avg_Pressure"].tolist())
    return pd.DataFrame([
        _test_record("全体差（モデル平均）", "Model", model_stats),
        _test_record("全体差（タスク平均）", "Task", task_stats),
    ])


# ==========================================
# 3. CSV 出力 (CSV Writers)
# ==========================================


def write_csvs(
    overall_df: pd.DataFrame,
    pivot_df: pd.DataFrame,
    dirs: dict[str, Path],
    model_summary: pd.DataFrame | None = None,
    task_summary: pd.DataFrame | None = None,
    statistical_tests: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """results/ 以下のすべての CSV を書き出し、モデル別サマリーを返します。"""
    overall_df.to_csv(dirs["overall_score"] / "overall_score.csv", index=False, encoding="utf-8-sig")

    gap_by_task = pivot_df.sort_values(by=["Task", "Model"]).reset_index(drop=True)
    gap_by_task.to_csv(dirs["pressure_gap"] / "pressure_gap_by_task.csv", index=False, encoding="utf-8-sig")

    if model_summary is None:
        model_summary = _calculate_model_summary(pivot_df, overall_df)
    if task_summary is None:
        task_summary = _calculate_task_summary(pivot_df)
    if statistical_tests is None:
        statistical_tests = _calculate_statistical_tests(model_summary, task_summary)
    model_summary.to_csv(dirs["pressure_gap"] / "pressure_gap_by_model.csv", index=False, encoding="utf-8-sig")
    task_summary.to_csv(
        dirs["pressure_gap"] / "pressure_gap_by_task_summary.csv", index=False, encoding="utf-8-sig"
    )
    statistical_tests.to_csv(dirs["statistics"] / "statistical_tests.csv", index=False, encoding="utf-8-sig")

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

    cat_summary = pivot_df.groupby(["Category", "Model"])["Pressure"].mean().unstack(level="Model").reset_index()
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
        "statistics": out_path / "statistics",
    }

    # 生成前に前回の出力を丸ごと消す(タスクやモデルの削除・リネーム時に
    # 古い CSV/PNG が残り続けるのを防ぐ)。この 4 ディレクトリは本スクリプトの
    # 管轄なので、中身はすべて再生成可能な生成物であることを前提とする。
    for d in dirs.values():
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    # CSV 出力(モデル別サマリーはグラフ側でも使う)
    model_summary = _calculate_model_summary(pivot_df, overall_df)
    task_summary = _calculate_task_summary(pivot_df)
    statistical_tests = _calculate_statistical_tests(model_summary, task_summary)
    model_summary = write_csvs(
        overall_df,
        pivot_df,
        dirs,
        model_summary,
        task_summary,
        statistical_tests,
    )

    # グラフ描画(charts.py へ委譲)
    charts.render_all(overall_df, pivot_df, model_summary, dirs, CATEGORY_ORDER, statistical_tests)

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
    loop_counts, scoring_method = load_scoring_config(args.config)
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
    overall_df, pivot_df = parse_csv_data(csv_path, metadata, loop_counts, scoring_method)

    # 描画スタイルの適用
    charts.setup_style()

    # 分析 & 出力
    analyze_and_output(overall_df, pivot_df, output_dir)


if __name__ == "__main__":
    main()
