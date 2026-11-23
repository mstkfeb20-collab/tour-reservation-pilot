#!/usr/bin/env bash
# requirement-traceability.sh（COMMON-003）の PR 本文の扱いの自己テスト。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; pass=0; fail=0
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
mkdir -p "$w/docs/requirements" "$w/src/test"
printf '## REQ-001 予約\n\n- 完了条件:\n  - 予約できる\n\n## テスト仕様\n\n- 予約を確かめる\n' > "$w/docs/requirements/a.md"
printf '## REQ-002 取消\n\n- 完了条件:\n  - 取り消せる\n\n## テスト仕様\n\n- 取消を確かめる\n' > "$w/docs/requirements/b.md"
echo '@Tag("REQ-001")' > "$w/src/test/ATest.java"

# case_ <名前> <期待（ok|ng）> <TAZUNA_IS_PR> <本文> [期待するメッセージ]
case_() {
  local out rc got=ok
  out=$(cd "$w" && TAZUNA_ROOT="$w" TAZUNA_IS_PR="$3" TAZUNA_PR_BODY="$4" bash "$ROOT/scripts/lint/common/requirement-traceability.sh" 2>&1); rc=$?
  [ "$rc" -ne 0 ] && got=ng
  if [ "$got" = "$2" ] && { [ -z "${5:-}" ] || grep -qF -- "$5" <<<"$out"; }; then pass=$((pass + 1))
  else fail=$((fail + 1)); echo "NG: $1（期待 $2、結果 $got）"; echo "$out" | sed 's/^/    /'; fi
}
case_ "対象要件にテストがある" ok 1 $'概要\n\n対象要件: REQ-001'
case_ "対象要件にテストがない" ng 1 $'対象要件: REQ-001, REQ-002' "REQ-002 を確かめるテストがありません"
case_ "対象要件: なし" ok 1 $'対象要件: なし'
case_ "PR なのに対象要件の行がない" ng 1 $'概要だけ' "「対象要件:」の行がありません"
case_ "PR の本文が空" ng 1 "" "「対象要件:」の行がありません"
case_ "引用の中の対象要件は行と見なさない" ng 1 $'> 対象要件: REQ-001' "「対象要件:」の行がありません"
case_ "PR でなければ対象要件の行は求めない" ok "" ""

echo "requirement-traceability: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
