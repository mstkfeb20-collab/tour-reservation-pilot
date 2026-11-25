#!/usr/bin/env bash
# tazuna（型）の新しいバージョンを、案件リポジトリに取り込む。
#
#   scripts/tazuna-update.sh v0.2.0               # 型のファイルを取り込む
#   scripts/tazuna-update.sh --id-design v0.2.0   # ID 設計の Excel だけを取り出す（何も上書きしない）
#
# - harness/tazuna-paths.txt に載っている型のファイルだけを、指定したタグの内容に置き換える
# - タグ側で削除された型のファイルは、案件側からも削除する
# - 案件のファイル（docs/、proj-* スキル、lint/domain など）には触れない
# - ID 設計の Excel（docs/design/ID設計.xlsx）は上書きしない。型と案件が書いたもの（機能一覧・書類一覧など）が
#   1つのファイルにあるため。型（書類の種類・記載項目・設計項目）が変わっていれば、新しい Excel と型の差分を
#   .tazuna-download/ に取り出すので、必要な行を案件の Excel に手で反映する
# - コミットはしない。差分を確認してから、案件リポジトリでPRを出す
#
# 取り込み元は環境変数 TAZUNA_REMOTE_URL で変えられる（GitLab の社内ミラーなど）。
set -euo pipefail
# 日本語のファイル名を引用符で囲ませない（囲まれると一覧のパターンに合わず、取り込まれない）
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.quotePath GIT_CONFIG_VALUE_0=false

ONLY_ID_DESIGN=0
if [ "${1:-}" = "--id-design" ]; then
  ONLY_ID_DESIGN=1
  shift
fi
TAG="${1:-}"
REMOTE_NAME="tazuna"
REMOTE_URL="${TAZUNA_REMOTE_URL:-https://github.com/mstkfeb20-collab/tazuna}"
XLSX="docs/design/ID設計.xlsx"
SNAP="docs/design/ID設計.md"
OUT=".tazuna-download"

if [ -z "$TAG" ]; then
  echo "使い方: scripts/tazuna-update.sh [--id-design] <タグ>（例: v0.2.0）" >&2
  exit 2
fi

cd "$(git rev-parse --show-toplevel)"

if [ -d _tazuna ]; then
  echo "ここは tazuna 本体です。型の修正はこのリポジトリで直接行ってください。" >&2
  exit 2
fi

if [ "$ONLY_ID_DESIGN" -eq 0 ] && { ! git diff --quiet || ! git diff --cached --quiet; }; then
  echo "未コミットの変更があります。コミットするか退避してから実行してください。" >&2
  exit 2
fi

# 取り込み元を2つ目のリモートとして登録する（初回のみ）
if ! git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  git remote add "$REMOTE_NAME" "$REMOTE_URL"
fi
fetch_tag() { git fetch --quiet "$REMOTE_NAME" "refs/tags/$1:refs/tags/$1"; }
fetch_tag "$TAG"
ref="refs/tags/$TAG"

# 取り込みの手順そのものが新しいタグで変わっていれば、新しい方で実行し直す
if [ -z "${TAZUNA_UPDATE_REEXEC:-}" ] && [ "$ONLY_ID_DESIGN" -eq 0 ]; then
  new_script=$(mktemp)
  if git show "$ref:scripts/tazuna-update.sh" > "$new_script" 2>/dev/null && ! cmp -s "$new_script" scripts/tazuna-update.sh; then
    echo "（取り込みの手順が $TAG で変わっているので、新しい手順で実行します）"
    TAZUNA_UPDATE_REEXEC=1 exec bash "$new_script" "$TAG"
  fi
  rm -f "$new_script"
fi

# ID 設計の型の部分（書類の種類・記載項目・設計項目）。機能一覧・書類一覧は案件が書くので比べない
type_part() { git show "$1:$SNAP" 2>/dev/null | sed -n '/^## 書類の種類/,$p'; }
project_type_part() { sed -n '/^## 書類の種類/,$p' "$SNAP" 2>/dev/null; }

# 新しいタグの Excel と型の差分を取り出す。取り出したら 0、型が変わっていなければ 1
#   前のタグがあれば、前のタグと新しいタグの型を比べて変わったかを決める（tazuna で変わったところ）
#   前のタグがなければ（手で取り込んできた案件など）、案件の書き出しと新しいタグの型を比べる
download_id_design() {
  local old="$1" has_old=0 f
  if [ -n "$old" ] && [ "$old" != "$TAG" ] && git rev-parse -q --verify "refs/tags/$old" >/dev/null; then has_old=1; fi
  if [ "$ONLY_ID_DESIGN" -eq 0 ]; then
    if [ "$has_old" -eq 1 ]; then
      [ "$(type_part "refs/tags/$old")" = "$(type_part "$ref")" ] && return 1
    else
      [ "$(project_type_part)" = "$(type_part "$ref")" ] && return 1
    fi
  fi
  mkdir -p "$OUT"
  printf '*\n' > "$OUT/.gitignore"   # 取り出したものはコミットしない
  git show "$ref:$XLSX" > "$OUT/ID設計-$TAG.xlsx"
  echo "  - $OUT/ID設計-$TAG.xlsx（$TAG の ID 設計の Excel。機能一覧・書類一覧は見本のまま）"
  if [ "$has_old" -eq 1 ]; then
    f="$OUT/ID設計の型の差分-$old-$TAG.diff"
    diff -u --label "$old" --label "$TAG" <(type_part "refs/tags/$old") <(type_part "$ref") > "$f" || true
    if [ -s "$f" ]; then echo "  - $f（tazuna で $old から $TAG までに変わった、書類の種類・記載項目・設計項目の行）"
    else rm -f "$f"; echo "  - tazuna では $old から $TAG までに型の行は変わっていません"; fi
  fi
  f="$OUT/ID設計の型の差分-案件-$TAG.diff"
  diff -u --label "案件の $SNAP" --label "$TAG" <(project_type_part) <(type_part "$ref") > "$f" || true
  if [ -s "$f" ]; then echo "  - $f（案件の Excel と $TAG の型の違い。案件で変えた「状態」「記載」の行も出る）"
  else rm -f "$f"; echo "  - 案件の Excel の型の行は $TAG と同じです"; fi
  return 0
}

old_tag=$(cat harness/tazuna-version 2>/dev/null || true)
[ -n "$old_tag" ] && fetch_tag "$old_tag" 2>/dev/null || true

if [ "$ONLY_ID_DESIGN" -eq 1 ]; then
  echo "ID 設計の Excel を取り出しました（案件のファイルは何も変えていません）:"
  download_id_design "$old_tag" || true
  exit 0
fi

# 新しいタグ側の一覧を正とする（一覧自体の更新も反映するため）
patterns=$(git show "$ref:harness/tazuna-paths.txt" | grep -vE '^[[:space:]]*(#|$)')

matches() {
  local f="$1" p
  # ID 設計の Excel と書き出しは、一覧に載っていても上書きしない（古い一覧から取り込むとき）
  case "$f" in "$XLSX"|"$SNAP") return 1 ;; esac
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
echo "ID 設計の Excel（$XLSX）は上書きしていません。"
id_changed=0
if download_id_design "$old_tag"; then
  id_changed=1
  echo "  型（書類の種類・記載項目・設計項目）が変わっています。差分を見て、必要な行を案件の Excel に手で反映してください。"
else
  echo "  型（書類の種類・記載項目・設計項目）は変わっていません。"
fi
echo
echo "次の手順:"
echo "  1. 差分を確認する（git diff --cached）"
step=2
if [ "$id_changed" -eq 1 ]; then
  echo "  $step. $OUT/ の差分を見て案件の $XLSX に反映し、python3 scripts/design/id_design.py export と paint を実行する（新しいツールが型の新しい列や項目を前提にしていることがある）"
  step=$((step + 1))
fi
echo "  $step. scripts/lint/run-all.sh と bash .github/hooks/tests/test-guard.sh を実行する"
echo "  $((step + 1)). deny-commands.txt・protected-paths.txt は案件のファイルなので取り込まれない。tazuna 側の同名ファイルと見比べ、型の部分の変更を手で反映する"
echo "  $((step + 2)). ブランチを切ってコミットし、案件リポジトリでPRを出す"
