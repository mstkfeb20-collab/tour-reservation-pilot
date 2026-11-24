#!/usr/bin/env bash
# review_pack.py（設計書レビューの材料）の自己テスト。tazuna 本体では評価セットで、案件では自分の設計書で動くことを確かめる。
set -u
cd "$(dirname "$0")/../../.." || exit 2
E=_tazuna/design-review/eval
if [ -d "$E" ]; then out=$(python3 scripts/design/review_pack.py --root "$E" --design "$E/design" 2>&1); rc=$?
elif [ -f docs/design/ID設計.md ]; then out=$(python3 scripts/design/review_pack.py 2>&1); rc=$?
else echo "review-pack: 設計書がないので飛ばしました"; exit 0; fi
pass=0; fail=0
check() { if grep -qF -- "$2" <<<"$out"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: $1（「$2」がない）"; fi; }
[ "$rc" -eq 0 ] && pass=$((pass + 1)) || { fail=$((fail + 1)); echo "NG: 実行に失敗"; echo "$out" | tail -5; }
check "見出し" "# 設計書レビューの材料"
check "同じ設計項目の節" "## 1. 同じ設計項目の行が2つ以上の書類にあるもの"
check "定義の一覧の節" "## 2. 定義の一覧"
check "決定とテスト仕様の節" "## 3. 機能ごとの決定とテスト仕様"
if [ -d "$E" ]; then
  check "共通と機能の行を並べる" "- [共通] S-11-001/D-06003/1"
  check "DDL の列と CHECK" "RESERVE: RESERVE_NO"
  check "テスト仕様の行を分ける" "- [テスト仕様] S-26-002/D-15001/1"
fi
echo "review-pack: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
