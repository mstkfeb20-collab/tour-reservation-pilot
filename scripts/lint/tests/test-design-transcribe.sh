#!/usr/bin/env bash
# scripts/design/transcribe.py の自己テスト。
# 転記・作り直し（冪等）・手書きの保持・テスト仕様のまとめ方・「要転記」と「手で直した」の見分けを確かめる。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; PY="$ROOT/scripts/design/transcribe.py"; SNAP="$ROOT/scripts/lint/tests/snapshot-for-test.py"
pass=0; fail=0
ok() { pass=$((pass + 1)); }
ng() { fail=$((fail + 1)); echo "NG: $1"; }

w=$(mktemp -d); mkdir -p "$w/docs/design"
python3 "$SNAP" "$w/docs/design/ID設計.md" "S-22-001|予約登録|" "S-26-001|予約登録|S-22-001"
cat > "$w/docs/design/S-22-001_予約登録.md" <<'MD'
# S-22-001 処理設計書：予約登録

## D-03002 相関チェック

- S-22-001-001 大人人数と子供人数の合計が1人以上であること

## D-04009 例外的な業務判断

- S-22-001-002 10人以上の団体は窓口担当が個別に見積もる

## D-03001 単項目チェック

- S-22-001-003 （廃止）画面設計書へ移した
MD
cat > "$w/docs/design/S-26-001_予約登録.md" <<'MD'
# S-26-001 テスト仕様書：予約登録

## D-15001 テスト観点・ケース

- S-26-001-001 同じ受付トークンで2回確定しても、予約は1件だけ登録される
MD
run() { TAZUNA_ROOT="$w" python3 "$PY" --design "$w/docs/design" --out "$w" "$@" >/dev/null 2>&1; }
status() { (cd "$ROOT/scripts/design" && python3 -c "import transcribe,sys; print(transcribe.status(sys.argv[1], sys.argv[2]).get('S-22-001'))" "$w/docs/design" "$w"); }
req="$w/docs/requirements/S-22-001_予約登録.md"

[ "$(status)" = "未転記" ] && ok || ng "転記前は未転記（$(status)）"
run --check && ok || ng "転記前はエラーにしない（①と②の間は正常）"
run
grep -q '^## REQ-22001 予約登録' "$req" && grep -q '合計が1人以上であること（S-22-001-001・相関チェック）' "$req" && ok || ng "要件の完了条件に転記される"
grep -q '10人以上の団体' "$req" && ok || ng "AIへの条件は要件ファイルの条件に入る"
grep -q 'S-22-001-003' "$req" && ng "廃止の行は転記しない" || ok
grep -q '^## テスト仕様：予約登録（S-26-001）' "$req" && grep -q '同じ受付トークン' "$req" && ok || ng "テスト仕様書はテスト仕様の節に入る"
grep -q 'REQ-26001' "$req" && ng "テスト仕様書から別の要件は作らない" || ok
[ ! -e "$w/docs/requirements/S-26-001_予約登録.md" ] && ok || ng "テスト仕様書だけの要件ファイルは作らない"
[ "$(status)" = "済" ] && ok || ng "転記した後は済（$(status)）"
cp "$req" "$w/before"; run; cmp -s "$req" "$w/before" && ok || ng "作り直しても変わらない（冪等）"
printf '\n手で書いたメモ\n' >> "$req"; run; grep -q '手で書いたメモ' "$req" && ok || ng "目印の外の手書きは残る"
sed -i 's/合計が1人以上であること/合計が2人以上であること/' "$req"
run --check && ng "転記した部分を手で直すとエラー" || ok
run; grep -q '合計が1人以上' "$req" && ok || ng "転記し直すと設計書の内容に戻る"
sed -i 's/合計が1人以上であること/合計が1人以上9人以下であること/' "$w/docs/design/S-22-001_予約登録.md"
run --check && ok || ng "設計書だけ先に直したときはエラーにしない"
[ "$(status)" = "要転記" ] && ok || ng "設計書だけ先に直すと要転記（$(status)）"
run; grep -q '1人以上9人以下' "$req" && [ "$(status)" = "済" ] && ok || ng "転記し直すと済に戻る"
rm -rf "$w"

echo "design-transcribe: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
