/**
 * サイト全体で共有する定数。
 *
 * 評価数値は手動で書かず、scripts/generate_results.py が results/*.csv から
 * 生成する results.json を参照する(更新手順: aggregate.py 実行後に
 * `pnpm gen:data` → コミット&プッシュ)。
 */
import results from './results.json';

export const GITHUB_REPO = 'https://github.com/Akikukeo1/alignment-under-pressure-benchmark';

export const KAGGLE_BENCHMARK =
	'https://www.kaggle.com/benchmarks/akikukeo1/alignment-under-pressure-benchmark';

/** GitHub raw ファイルへの直リンク基底URL */
export const RAW_BASE =
	'https://raw.githubusercontent.com/Akikukeo1/alignment-under-pressure-benchmark/main/';

/** モデル名の短縮表示(末尾の -default / -preview を省く) */
export function shortModel(model: string): string {
	return model.replace(/-default$/, '').replace(/-preview$/, '');
}

/**
 * ランディングのハイライト数値(results.json 由来・自動更新)。
 */
export const HIGHLIGHTS = {
	/** 総合スコアの最高値(100点満点) */
	topScore: results.overall[0]?.score ?? 0,
	/** 最高スコアのモデル(短縮名) */
	topModel: shortModel(results.overall[0]?.model ?? ''),
	/** 評価済みモデル数 */
	models: results.meta.models,
	/** 基本タスク数(Normal対照は別途自動生成) */
	tasks: results.meta.tasks,
	/** 評価カテゴリ数(Bias/Ethics/Logic/Robustness/Safety) */
	categories: results.meta.categories.length,
	/** 圧力耐性スコアの最高値(0〜1) */
	bestResistance: results.meta.bestResistance,
	/** データ最終更新日 */
	dataUpdated: results.meta.updated,
} as const;
