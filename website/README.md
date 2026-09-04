# AUPB Webサイト

`website/` は Astro + Starlight で構成された AUPB の公開サイトです。
評価結果、タスクのプロンプト全文、論文 PDF、透明性と再現性に関する説明を提供します。

リポジトリ全体のドキュメント構成は [docs/README.md](../docs/README.md) を参照してください。

## 前提条件

- Node.js: `website/.node-version` に記載されたバージョン
- pnpm: `pnpm-lock.yaml` と互換性のあるバージョン
- Python / uv: ルートの生成スクリプトを実行するために必要
- `results/`、`tasks/`、`paper/dist/figures/`: データページを生成する場合に必要

## よく使うコマンド

コマンドは、原則としてリポジトリのルートで `just` レシピを使います。

| コマンド | 用途 |
| :--- | :--- |
| `just site` | 本番サイトをビルドし、`website/dist/` を生成 |
| `just dev` | 開発サーバーをバックグラウンドで起動 |
| `just dev-status` | 開発サーバーの状態を確認 |
| `just dev-stop` | 開発サーバーを停止 |
| `just sync-docs` | ルートの `REPRODUCIBILITY.md` をサイト用 MDX へ同期 |
| `just sync-data` | `results/` からサイト用 JSON と画像を生成 |
| `just update` | 集計からサイトビルドまでを一括実行 |

初回のセットアップとサイト単体の確認:

```bash
cd website
pnpm install
pnpm dev
```

Windows の実行ポリシーによって `pnpm.ps1` が拒否される場合は、同じコマンドを `pnpm.cmd` で実行します。
たとえば `pnpm.cmd build` のように拡張子を付けてください。

本番ビルドは次のコマンドで確認できます。

```bash
cd website
pnpm build
```

## 更新ルール

### 再現手順

再現手順の正本はルートの `REPRODUCIBILITY.md` です。
`website/src/content/docs/reproducibility.mdx` は生成物なので直接編集せず、
変更後に次を実行してください。

```bash
just sync-docs
```

### タスク一覧

`website/src/content/docs/tasks.mdx` の導入文と、`website/src/components/tasks/TaskPrompts.astro`
の表示ロジックを使い、サイトのビルド時にルートの `tasks/*.toml` を読み込みます。
タスクの本文や grader を変更するときは TOML を編集してください。

### 結果データ

`website/src/data/results.json` と `website/public/results/` は、`results/` と論文用図から生成されます。
直接編集せず、次の順に実行してください。

```bash
just aggregate
just figures
just sync-data
```

`just sync-data` は、サイトで使う JSON と PNG を一度削除してから再生成します。
結果ページの表示だけを変更する場合は、`website/src/content/docs/results.mdx` または対応する Astro コンポーネントを編集します。

### 論文 PDF と版履歴

`website/public/paper.pdf` は公開用 PDF、`website/src/data/paper.json` は論文の版履歴です。
正式版の公開処理は GitHub Actions の `publish-paper.yml` が担当します。
PDF の表示や版履歴の UI を変更する場合は `PaperViewer.astro` と関連データを確認してください。

## 主なディレクトリ

| パス | 役割 |
| :--- | :--- |
| `src/content/docs/` | Starlight の公開ドキュメントページ |
| `src/components/` | 結果表、タスク一覧、論文ビューアなどの表示部品 |
| `src/data/` | 生成された結果・論文メタデータ |
| `scripts/` | 結果データ・再現手順などの同期スクリプト |
| `public/` | PDF、画像、favicon などの静的ファイル |
| `astro.config.mjs` | サイト設定とサイドバー構成 |

## 確認

サイトの変更後は、少なくとも次を実行してください。

```bash
just site
```

Python 側の生成処理を変更した場合は、追加で `just lint` を実行します。
