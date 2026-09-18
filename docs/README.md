# ドキュメント案内

AUPB のドキュメントは、読む目的ごとに次の場所へ分かれています。
最初に全体像を知りたい場合は、[ルートの README](../README.md) から読み始めてください。

## 目的別の入口

| 目的 | 文書 | 内容 |
| :--- | :--- | :--- |
| プロジェクトの概要を知る | [README.md](../README.md) | ベンチマークの目的、構成、主要コマンド |
| 評価結果を再現する | [REPRODUCIBILITY.md](../REPRODUCIBILITY.md) | 環境構築、タスクのビルド、Kaggle 実行、集計、サイト反映 |
| タスクを追加・修正する | [TASK_SCHEMA.md](TASK_SCHEMA.md) | TOML のスキーマ、grader、難易度、バリデーション |
| スコアの意味を確認する | [SCORING.md](SCORING.md) | タスクスコア、Gap、圧力耐性比、集計と不確実性 |
| 特定タスクの設計経緯を読む | [chess_pressure_revision.md](chess_pressure_revision.md) | chess タスクの圧力条件を見直した際の設計メモ |
| 論文の定義・主張を読む | [paper/main.tex](../paper/main.tex) | 論文本文と研究上の説明 |
| Webサイトを開発・更新する | [website/README.md](../website/README.md) | サイトのビルド、データ同期、文書同期、開発サーバー |

## 正本と生成物

同じ内容を複数の場所に手で書くと、更新漏れが起きます。次のファイルを正本として扱います。

| 正本 | 生成・表示先 | 更新方法 |
| :--- | :--- | :--- |
| `REPRODUCIBILITY.md` | `website/src/content/docs/reproducibility.mdx` | ルートの文書を編集後、`just sync-docs` |
| `tasks/*.toml` | Webサイトのタスク一覧 | TOML を編集後、`just site`（ビルド時に読み込み） |
| `results/` | `website/src/data/results.json`、`website/public/results/*.png` | `just aggregate` → `just figures` → `just sync-data` |
| `paper/main.tex` と `paper_figures.py` | 論文 PDF・論文用図 | CI または再現手順の論文図生成手順 |

生成物は原則として直接編集しません。特に `website/src/content/docs/reproducibility.mdx`、
`website/src/data/results.json`、`website/public/results/` は、対応する正本または生成スクリプトを更新してください。

## よく使う更新フロー

### 文書だけを更新する

1. ルートの正本または `website/src/content/docs/` の対象ページを編集する
2. 再現手順を変更した場合は `just sync-docs` を実行する
3. `just site` でサイトのビルドを確認する

### タスク・評価結果を更新する

1. `tasks/*.toml` またはリーダーボード CSV を更新する
2. `just update` を実行する
3. 変更された `results/` とサイト内データを確認する

`just update` は集計、論文図、サイトデータ、再現手順ページの同期、サイトビルドを順に実行します。
リーダーボード CSV が不要な文書変更では、`just update` ではなく必要なレシピだけを実行してください。

