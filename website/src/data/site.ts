/**
 * サイト全体で共有する定数。
 * 結果の更新時は HIGHLIGHTS の数値を書き換える(手動更新)。
 */

export const GITHUB_REPO = 'https://github.com/Akikukeo1/alignment-under-pressure-benchmark';

export const KAGGLE_BENCHMARK =
	'https://www.kaggle.com/benchmarks/akikukeo1/alignment-under-pressure-benchmark';

/** GitHub raw ファイルへの直リンク基底URL */
export const RAW_BASE =
	'https://raw.githubusercontent.com/Akikukeo1/alignment-under-pressure-benchmark/main/';

/**
 * ランディングのハイライト数値。
 * 出典: results/overall_score/overall_score.csv, results/pressure_gap/pressure_resistance.csv
 */
export const HIGHLIGHTS = {
	/** 総合スコアの最高値(100点満点) */
	topScore: 87.5,
	/** 最高スコアのモデル */
	topModel: 'claude-opus-4-8',
	/** 評価済みモデル数 */
	models: 5,
	/** 基本タスク数(Normal対照は別途自動生成) */
	tasks: 8,
	/** 評価カテゴリ数(Bias/Ethics/Logic/Robustness/Safety) */
	categories: 5,
	/** 圧力耐性スコアの最高値(0〜1) */
	bestResistance: 0.75,
	/** データ最終更新日 */
	dataUpdated: '2026-07-30',
} as const;
