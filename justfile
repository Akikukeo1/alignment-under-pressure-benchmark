# AUPB ビルドタスクランナー
# 使い方: `just` でレシピ一覧表示 / `just <レシピ名>` で実行

# Windows 環境では PowerShell / それ以外は bash を使用する。
# 注意: Windows PowerShell 5.1 は && 非対応のため、レシピ内の連結は ; を使う。
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]
set shell := ["bash", "-cu"]

# 既定: レシピ一覧を表示
default:
    @just --list

# 集計CSVとグラフ画像を再生成(results/ 以下を更新)
aggregate:
    uv run aggregate.py

# 論文と同一ロジックの公式図を生成(results/figures/ に出力)
figures:
    uv run paper_figures.py --input akikukeo1_alignment-under-pressure-benchmark_leaderboard.csv

# ウェブサイト用データを生成(results.json とサイト内画像を更新)
sync-data:
    cd website; pnpm gen:data

# ウェブサイトをビルド(website/dist/ に静的ファイルを出力)
site:
    cd website; pnpm build

# 評価データ更新 → サイト反映までの一連フロー(全自動)
update: aggregate figures sync-data site

# Python の Lint チェック
lint:
    uv run ruff check .

# 開発サーバーをバックグラウンドで起動
dev:
    cd website; npx astro dev --background

# 開発サーバーの状態を確認
dev-status:
    cd website; npx astro dev status

# 開発サーバーを停止
dev-stop:
    cd website; npx astro dev stop
