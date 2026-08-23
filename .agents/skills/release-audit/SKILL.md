---
name: release-audit
description: GitHubリポジトリをPublic公開する前の安全監査を読み取り専用で実行する。全Git履歴(削除済みファイル・到達不能オブジェクト含む)まで調査し、秘密情報・個人情報・設定ファイル・ライセンス・論文公開適合性・巨大バイナリ・gitignore仕様を精査してseverity付きで報告する。
argument-hint: "(任意) 重点確認したい領域"
disable-model-invocation: true
---

# Release Audit(Public公開前リポジトリ監査)

GitHubリポジトリを完全にPublic化する前に行うべき監査を、**読み取り専用**で実行する。

## 目的と原則

- **ファイルは変更しない。git操作(add / commit / push 等)も行わない。** 監査と報告に徹する。修正はユーザーが明示的に指示した場合のみ別途行う。
- 応答は日本語。
- 推測ではなく、**実際のリポジトリ内容(コマンド出力)を根拠**にする。
- 「現在の作業ツリーに存在しない」だけでは安全と判定**しない**。Git履歴・削除済みファイル・到達不能オブジェクトまで調査する。
- 引数で重点領域が指定された場合は、その領域を優先的に深掘りする。

## 手順0: 基本情報の収集

```bash
ls -la
git status --short --untracked-files=normal
git log --all --oneline        # コミットメッセージ自体の機密漏れも目視する
git branch -a -v; git remote -v
git stash list; git tag
```

ブランチは `--all` で全参照を確認する。stash にも機密が残る場合がある。

## 手順1: 秘密情報スキャン(全履歴)

以下のパターンを全コミットに対して走査する:

| パターン | 対象 |
| :--- | :--- |
| `api_key`, `apikey`, `secret`, `password`, `passwd`, `token`, `Bearer ` | 汎用 |
| `sk-[A-Za-z0-9]` | OpenAI 系 |
| `AIza[A-Za-z0-9_-]` | Google API key |
| `ghp_` / `gho_` / `github_pat` | GitHub token |
| `AKIA[A-Z0-9]` | AWS access key |
| `BEGIN.*PRIVATE KEY` | 秘密鍵 |
| `"username":.*"key":` | kaggle.json 形式 |

実行方法:

```bash
for pat in "api_key\|apikey" "secret" "password\|passwd" "token" "Bearer " \
           "sk-[A-Za-z0-9]" "AIza[A-Za-z0-9_-]" "ghp_\|gho_\|github_pat" \
           "AKIA[A-Z0-9]" "BEGIN.*PRIVATE KEY"; do
  git grep -I -i -n "$pat" $(git rev-list --all) -- 2>/dev/null
done
```

判定上の注意:

- ヒットは必ず周辺文脈を読んで**実キーか偽陽性かを判定**する。`process.env` / `os.environ` / `getenv` 参照、ドキュメント内の説明文、lock ファイルは除外してよい。ベンチマークの問題文中の「password」等はコンテンツであり秘密情報ではない。
- プレースホルダー(`kaggle:xx` 等)と実キーの形式の違いを見分ける。

特定の機密ファイルが履歴に一度も存在しないことの検証(`.env` 等):

```bash
git rev-list --all | while read c; do
  if git cat-file -e $c:.env 2>/dev/null; then echo "FOUND .env in commit $c"; fi
done
```

> 実際の秘密ファイルの中身を読む必要が出た場合はユーザーに許可を求める。拒否された場合は、履歴不在の検証結果のみを根拠として報告し、中身には触れない。

## 手順2: 到達不能オブジェクトの調査

`git add` 後に取り消した内容などは、履歴から到達不能な blob として残存する。

```bash
git fsck --unreachable --no-progress
git cat-file -s <hash>                  # サイズ
git cat-file -p <hash> | head -c 400    # 中身を必ず確認する
```

古い版のスクリプト等で無害なことが多いが、staged した秘密情報の残留がないか中身を目視する。

## 手順3: 削除済みファイルの調査

```bash
git log --all --diff-filter=D --name-only --format='COMMIT %h' | sort -u
git show <rev>:<path> | head -50   # 削除済みファイルの中身を確認
```

notebook・workflow 定義・設定ファイルはトークン混入率が高いため優先的に確認する。

## 手順4: 作者情報(個人情報)

```bash
git log --all --format='%an <%ae>' | sort | uniq -c   # author
git log --all --format='%cn <%ce>' | sort | uniq -c   # committer
```

- noreply アドレス以外の実メールアドレスがあれば Medium〜High。
- CSV・PDF・ドキュメント内の氏名・電話番号・住所も `git grep` で補助走査する。

## 手順5: 大きなblob・不要ファイル

```bash
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '$1=="blob" && $3 > 100000 {printf "%.1fMB %s\n", $3/1048576, $4}' | sort -rn | head -25
```

- 追跡済みの不要物: `__pycache__/`、`*.pyc`、空ファイル、ビルド成果物。
- 削除済みでも履歴に残る巨大blobは公開可否とは別に肥大化要因として報告する。

## 手順6: 設定ファイル・成果物の公開適合性

- `.env` 系: 実在するか、無視設定されているか。**内容の読み取りは手順1の注意に従う。**
- PDF 等バイナリ成果物のメタデータ(Author 欄等):

```bash
grep -a -o -E "/(Title|Author|Creator|Producer) ?\([^)]{0,120}\)" <pdf>
```

圧縮ストリーム内の本文テキストは自動検査できないため、「本文中の著者名・所属は目視確認が必要」と明記して報告する。

- 論文PDFを同梱する場合、査読先の二重投稿ポリシー・匿名レビュー要件との整合を確認事項として挙げる。

## 手順7: ライセンス

```bash
find . -iname "LICENSE*" -not -path "./.venv/*" -not -path "./.git/*"
```

- LICENSE 不在なら High(デフォルトで「無断転載禁止」扱いとなり再利用不能)。
- サードパーティ同梱物(skill・フォント・画像等)の出所を `skills-lock.json` 等と照合し、再配布条件を確認する。lock 記載のない同梱物は出所不明として指摘する。

## 手順8: gitignore 仕様の検証

仕様メモ(監査・修正時の重要ポイント):

- パターン途中に `/` を含むとその .gitignore の位置基準で固定される。任意階層に効かせたい場合は `**/` を使う。
- **除外されたディレクトリ配下のファイルは `!` でも再包含できない**(親ディレクトリ自体の除外が優先される)。
- ホワイトリスト方式は「子レベルを `*` で除外 + 特定の子ディレクトリを `!` で再包含」で実現する(本リポジトリの運用):

  ```gitignore
  **/.agents/skills/*
  !**/.agents/skills/paper-review/
  !**/.agents/skills/release-audit/
  ```

- 追跡済みファイルは ignore 追加後も追跡され続ける → `git rm --cached` が必要。

検証コマンド:

```bash
git check-ignore -v <path>            # 意図したパターン行で一致するか必ず確認
git ls-files --others --directory     # 未追跡一覧(無視されていないものが見える)
```

## 手順9: 報告フォーマット

各問題について次の項目を揃えて報告する:

| 項目 | 内容 |
| :--- | :--- |
| severity | Critical / High / Medium / Low |
| 対象 | ファイルまたはコミット(hash を明記) |
| 内容 | 問題の事実(根拠となる出力を添える) |
| 理由 | なぜ公開前に問題なのか |
| 推奨対応 | 具体的な対処案 |

最後に**公開前チェックリスト**(優先順)を付す。重大発見(Critical)時は他の作業より先に即座に報告する。
