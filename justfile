# AUPB ビルドタスクランナー
# 使い方: `just` でレシピ一覧表示 / `just <レシピ名>` で実行

# Windows 環境でも bash を使って各レシピを実行する
set shell := ["bash", "-cu"]

# 既定: レシピ一覧を表示
default:
    @just --list

# 集計CSVとグラフ画像を再生成(results/ 以下を更新)
aggregate:
    uv run aggregate.py

# ウェブサイト用データを生成(results.json とサイト内画像を更新)
sync-data:
    cd website && pnpm gen:data

# ウェブサイトをビルド(website/dist/ に静的ファイルを出力)
site:
    cd website && pnpm build

# 評価データ更新 → サイト反映までの一連フロー(全自動)
update: aggregate sync-data site

# Python の Lint チェック
lint:
    uv run ruff check .

# 開発サーバーをバックグラウンドで起動
dev:
    cd website && npx astro dev --background

# 開発サーバーの状態を確認
dev-status:
    cd website && npx astro dev status

# 開発サーバーを停止
dev-stop:
    cd website && npx astro dev stop
