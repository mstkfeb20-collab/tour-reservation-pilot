#!/usr/bin/env bash
# tazuna（型）の新しいバージョンを、案件リポジトリに取り込む。
#
#   scripts/tazuna-update.sh v0.2.0
#
# - harness/tazuna-paths.txt に載っている型のファイルだけを、指定したタグの内容に置き換える
# - タグ側で削除された型のファイルは、案件側からも削除する
# - 案件のファイル（docs/、proj-* スキル、lint/domain など）には触れない
# - コミットはしない。差分を確認してから、案件リポジトリでPRを出す
#
# 取り込み元は環境変数 TAZUNA_REMOTE_URL で変えられる（GitLab の社内ミラーなど）。
set -euo pipefail

TAG="${1:-}"
REMOTE_NAME="tazuna"
REMOTE_URL="${TAZUNA_REMOTE_URL:-https://github.com/mstkfeb20-collab/tazuna}"

if [ -z "$TAG" ]; then
  echo "使い方: scripts/tazuna-update.sh <タグ>（例: v0.2.0）" >&2
  exit 2
fi

cd "$(git rev-parse --show-toplevel)"

if [ -d _tazuna ]; then
  echo "ここは tazuna 本体です。型の修正はこのリポジトリで直接行ってください。" >&2
  exit 2
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "未コミットの変更があります。コミットするか退避してから実行してください。" >&2
  exit 2
fi

# 取り込み元を2つ目のリモートとして登録する（初回のみ）
if ! git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  git remote add "$REMOTE_NAME" "$REMOTE_URL"
fi
git fetch --quiet "$REMOTE_NAME" "refs/tags/$TAG:refs/tags/$TAG"

ref="refs/tags/$TAG"

# 新しいタグ側の一覧を正とする（一覧自体の更新も反映するため）
patterns=$(git show "$ref:harness/tazuna-paths.txt" | grep -vE '^[[:space:]]*(#|$)')

matches() {
  local f="$1" p
  while IFS= read -r p; do
    # shellcheck disable=SC2053
    [[ "$f" == $p ]] && return 0
  done <<< "$patterns"
  return 1
}

updated=0
removed=0

# 1. タグにある型のファイルを取り込む
while IFS= read -r f; do
  if matches "$f"; then
    git checkout "$ref" -- "$f"
    updated=$((updated + 1))
  fi
done < <(git ls-tree -r --name-only "$ref")

# 2. タグ側で削除された型のファイルを消す
tag_files=$(git ls-tree -r --name-only "$ref")
while IFS= read -r f; do
  if matches "$f" && ! grep -qxF "$f" <<< "$tag_files"; then
    git rm --quiet "$f"
    removed=$((removed + 1))
  fi
done < <(git ls-files)

echo "$TAG" > harness/tazuna-version
git add harness/tazuna-version

echo "tazuna $TAG を取り込みました（更新 ${updated} 件、削除 ${removed} 件）"
echo
git status --short
echo
echo "次の手順:"
echo "  1. 差分を確認する（git diff --cached）"
echo "  2. scripts/lint/run-all.sh と bash .github/hooks/tests/test-guard.sh を実行する"
echo "  3. deny-commands.txt・protected-paths.txt は案件のファイルなので取り込まれない。tazuna 側の同名ファイルと見比べ、型の部分の変更を手で反映する"
echo "  4. ブランチを切ってコミットし、案件リポジトリでPRを出す"
