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

# 論文用の公式図を生成(paper/dist/figures/ に出力、入力は aggregate.py の集計結果)
figures:
    uv run paper_figures.py --output-dir paper/dist/figures

# ウェブサイト用データを生成(results.json とサイト内画像を更新)
sync-data:
    cd website; pnpm gen:data

# 再現手順ページを生成(REPRODUCIBILITY.md → reproducibility.mdx)
sync-docs:
    cd website; uv run scripts/generate_repro.py

# ウェブサイトをビルド(website/dist/ に静的ファイルを出力)
site:
    cd website; pnpm build

# 評価データ更新 → サイト反映までの一連フロー(全自動)
# NOTE: 依存レシピ形式(update: aggregate figures ...)は windows-shell(PowerShell)設定下で
# 依存名がコマンドとして実行され失敗するため、明示的に just を呼び出す
update:
    just aggregate
    just figures
    just sync-data
    just sync-docs
    just site

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

vis:
    graphify extract . --code-only; graphify tree
