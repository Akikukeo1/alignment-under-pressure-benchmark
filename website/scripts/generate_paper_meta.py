"""GitHub Release タグから論文のバージョンメタデータを生成する。

生成物:
    - src/data/paper.json : 論文ページの「現行版」バッジとバージョン履歴のソース

使い方(リポジトリ直下で実行):
    uv run website/scripts/generate_paper_meta.py

publish-paper.yml は採番の直後(タグ作成前)に呼ぶため、env で今回分を上書きできる:
    - PAPER_CURRENT_VERSION          : 今回採番したバージョン(vX.Y)
    - PAPER_CURRENT_PUBLISHED_AT     : 公開時刻(ISO 8601 / 未指定なら現在時刻)

時刻はすべて UTC の ISO 8601 で保持する。タグ時刻も epoch 経由で取得するため、
実行環境のタイムゾーン設定(GitHub Actions ランナーは UTC、ローカルは JST など)
に結果が左右されない。JST への変換は表示側(PaperViewer.astro)がビルド時に
明示的に行う。

preview タグ(pipeline.yml の update-preview が main push ごとに削除&再作成する
ローリング運用)は時刻を持たせても即座に陳腐化するため、バージョン名のみを
別フィールドに出力し、正式版の versions には含めない。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

WEBSITE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = WEBSITE_DIR.parent
OUT_JSON = WEBSITE_DIR / "src" / "data" / "paper.json"

# 正式版タグ(vX.Y 厳密一致)。それ以外(preview 等)は先行公開版扱い。
STABLE_RE = re.compile(r"^v(\d+)\.(\d+)$")


def stable_key(version: str) -> tuple[int, int] | None:
    """正式版タグを (X, Y) の数値キーへ変換する。非正式版は None。"""
    m = STABLE_RE.match(version)
    return (int(m.group(1)), int(m.group(2))) if m else None


def collect_tags() -> list[dict[str, object]]:
    """全タグを版情報のリストで返す(正式版: 新しい順、先行公開版: その後に新しい順)。"""
    result = subprocess.run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)%09%(creatordate:unix)",
            "refs/tags",
        ],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    stable: list[tuple[int, int, dict[str, object]]] = []
    prereleases: list[dict[str, object]] = []
    # for-each-ref の出力は「名前<TAB>epoch」
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        name, ts = parts[0], parts[1]
        published_at = to_iso_utc(int(ts))
        entry: dict[str, object] = {
            "version": name,
            "publishedAt": published_at,
            "prerelease": STABLE_RE.match(name) is None,
        }
        m = STABLE_RE.match(name)
        if m:
            stable.append((int(m.group(1)), int(m.group(2)), entry))
        else:
            prereleases.append(entry)
    # 正式版は X 降順 → Y 降順。先行公開版は公開時刻の降順で正式版の後ろに置く。
    stable.sort(key=lambda t: (-t[0], -t[1]))
    prereleases.sort(key=lambda e: str(e["publishedAt"]), reverse=True)
    return [entry for _, _, entry in stable] + prereleases


def to_iso_utc(epoch_or_dt: int | datetime) -> str:
    """UTC の ISO 8601(Z 末尾)へ正規化する。"""
    if isinstance(epoch_or_dt, int):
        dt = datetime.fromtimestamp(epoch_or_dt, tz=UTC)
    else:
        dt = epoch_or_dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_env_time(raw: str) -> str:
    """PAPER_CURRENT_PUBLISHED_AT の時刻文字列を ISO 8601 として解釈し、正規化する。"""
    normalized = raw.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    return to_iso_utc(dt)


def apply_current_override(
    versions: list[dict[str, object]],
) -> dict[str, object] | None:
    """現行版の上書き指定(PAPER_CURRENT_VERSION)があれば適用し、current エントリを返す。"""
    version = os.environ.get("PAPER_CURRENT_VERSION", "").strip()
    if not version:
        return next((e for e in versions if not e["prerelease"]), None)

    published_at_raw = os.environ.get("PAPER_CURRENT_PUBLISHED_AT", "").strip()
    published_at = parse_env_time(published_at_raw) if published_at_raw else to_iso_utc(datetime.now(UTC))

    entry = next((e for e in versions if e["version"] == version), None)
    if entry is None:
        entry = {
            "version": version,
            "publishedAt": published_at,
            "prerelease": stable_key(version) is None,
        }
        key = stable_key(version)
        if key is not None:
            # 正式版は X/Y 降順を保つため、最初に「新より古い」版の直前へ挿入する
            index = len(versions)
            for i, existing in enumerate(versions):
                ekey = stable_key(str(existing["version"]))
                if ekey is not None and ekey < key:
                    index = i
                    break
            versions.insert(index, entry)
        else:
            versions.insert(0, entry)
    else:
        entry["publishedAt"] = published_at

    return entry


def restore_missing_versions(
    versions: list[dict[str, object]],
    existing_path: Path,
) -> None:
    """タグから取得できなかった過去版を既存 paper.json から復元する(保険)。

    CI の shallow clone などでタグが取得できない場合、versions が今回分だけに
    なり履歴が消えてしまう事故があった。既存ファイルにのみ存在する版を
    補完し、X/Y 降順に並べ替えて履歴の消失を防ぐ。
    """
    if not existing_path.exists():
        return
    try:
        existing = json.loads(existing_path.read_text(encoding="utf-8")).get("versions", [])
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: 既存 {existing_path.name} の読み込みに失敗したため復元をスキップします: {e}")
        return

    known = {str(v["version"]) for v in versions}
    restored = 0
    for entry in existing:
        if str(entry.get("version")) not in known:
            versions.append(entry)
            restored += 1
    if restored:
        versions.sort(
            key=lambda v: stable_key(str(v["version"])) or (0, 0),
            reverse=True,
        )
        print(f"既存 paper.json から {restored} 版を復元しました")


def main() -> None:
    tags = collect_tags()
    # 正式版のみを履歴対象にする。preview 等はローリング運用のためバージョン名のみ
    versions = [t for t in tags if not t["prerelease"]]
    previews = [t for t in tags if t["prerelease"]]
    preview = {"version": str(previews[0]["version"])} if previews else None
    restore_missing_versions(versions, OUT_JSON)
    current = apply_current_override(versions)

    data = {"current": current, "preview": preview, "versions": versions}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    label = current["version"] if current else "(なし)"
    print(f"[OK] {OUT_JSON.relative_to(REPO_DIR)} を生成(現行版: {label}・正式版 {len(versions)} 版)")


if __name__ == "__main__":
    main()
