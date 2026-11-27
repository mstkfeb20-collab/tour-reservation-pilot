#!/usr/bin/env bash
# scripts/design/review_record.py（COMMON-011）の自己テスト。
# 点検の記録がない・古い・止める種別が残る・質問が issue になっていない、を PR では止め、手元とドラフトでは警告にする。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; PY="$ROOT/scripts/design/review_record.py"; SNAP="$ROOT/scripts/lint/tests/snapshot-for-test.py"
pass=0; fail=0
ok() { pass=$((pass + 1)); }
ng() { fail=$((fail + 1)); echo "NG: $1"; }

w=$(mktemp -d); mkdir -p "$w/docs/design" "$w/docs/review"
python3 "$SNAP" "$w/docs/design/ID設計.md" "S-22-001|予約登録|"
printf '# S-22-001 処理設計書：予約登録\n\n## D-03002 相関チェック\n\n- [1] 大人人数と子供人数の合計が1人以上であること\n' > "$w/docs/design/S-22-001_予約登録.md"
rec="$w/docs/review/設計書の点検.tsv"
# check <期待 ok|ng> <名前> [環境変数...]
check() {
  local want="$1" name="$2"; shift 2
  out=$(env TAZUNA_ROOT="$w" "$@" python3 "$PY" check 2>&1); rc=$?
  if { [ "$want" = ok ] && [ $rc -eq 0 ]; } || { [ "$want" = ng ] && [ $rc -ne 0 ]; }; then ok; else ng "$name（rc=$rc）: $out"; fi
}
PR="TAZUNA_IS_PR=1"

check ok "手元では記録がなくても止めない"
echo "$out" | grep -q 'WARN  \[COMMON-011\].*点検の記録がありません' && ok || ng "手元では警告を出す"
check ng "設計書を変えた PR で記録がなければ止める" $PR
check ok "ドラフトの PR では止めない" $PR TAZUNA_PR_DRAFT=1
printf '種別\t根拠の行ID\t指摘\t扱い\n食い違い\tS-22-001/D-03002/1\t人数の上限が画面と違う\t\n質問\tS-22-001/D-03002/1\t団体の上限は何人か\t\n' > "$rec"
TAZUNA_ROOT="$w" python3 "$PY" stamp >/dev/null
head -1 "$rec" | grep -q '^# 点検した設計書の指紋: [0-9a-f]\{12\}$' && ok || ng "stamp は1行目に指紋を書く"
check ng "止める種別が残っていれば止める" $PR
echo "$out" | grep -q '残す: 理由' && echo "$out" | grep -q 'issue: #番号' && ok || ng "直し方（残す・issue）を示す"
sed -i 's/画面と違う\t$/画面と違う\t残す: 画面側を次の版で直す/; s/何人か\t$/何人か\tissue: #12/' "$rec"
check ok "残す理由と issue があれば通す" $PR
sed -i 's/1人以上/2人以上/' "$w/docs/design/S-22-001_予約登録.md"
check ng "点検の後に設計書を変えたら止める" $PR
echo "$out" | grep -q '点検の後に設計書が変わっています' && ok || ng "設計書が変わったことを伝える"
TAZUNA_ROOT="$w" python3 "$PY" stamp >/dev/null
check ok "点検し直して stamp すれば通す" $PR
[ "$(grep -c '^# 点検した設計書の指紋' "$rec")" = 1 ] && ok || ng "stamp を繰り返しても指紋の行は1つ"
rm -rf "$w"

echo "review-record: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
