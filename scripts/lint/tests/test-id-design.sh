#!/usr/bin/env bash
# scripts/design/id_design.py の自己テスト（openpyxl が要る）。
# 機能一覧からの書類一覧・番号の保持・廃止・「書かない」の保持・ひな形・書き出しの食い違い検出を確かめる。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; PY="$ROOT/scripts/design/id_design.py"
pass=0; fail=0
ok() { pass=$((pass + 1)); }
ng() { fail=$((fail + 1)); echo "NG: $1"; }
python3 -c 'import openpyxl' 2>/dev/null || { echo "openpyxl がないので飛ばします（pip install openpyxl）"; exit 0; }

w=$(mktemp -d); mkdir -p "$w/docs/design"; cp "$ROOT/docs/design/ID設計.xlsx" "$w/docs/design/"
x="$w/docs/design/ID設計.xlsx"; md="$w/docs/design/ID設計.md"
# 案件のリポジトリでも動くように、案件で書いたシート（機能一覧・書類一覧・進捗・網羅状況）を空にしてから試す
python3 - "$x" <<'PY'
import sys
from openpyxl import load_workbook
wb = load_workbook(sys.argv[1])
for s in ("機能一覧", "書類一覧", "進捗", "網羅状況"):
    ws = wb[s]
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)
wb.save(sys.argv[1])
PY
run() { (cd "$w" && TAZUNA_ROOT="$w" python3 "$PY" "$@" >/dev/null 2>&1); }
edit() { python3 - "$x" "$@" <<'PY'
import sys
from openpyxl import load_workbook
p = sys.argv[1]; wb = load_workbook(p); cmd = sys.argv[2]
if cmd == "func":
    wb["機能一覧"].append(sys.argv[3].split("|"))
elif cmd == "delfunc":
    ws = wb["機能一覧"]
    for i in range(ws.max_row, 1, -1):
        if ws.cell(i, 1).value == sys.argv[3]: ws.delete_rows(i)
elif cmd in ("retire", "unused"):
    ws = wb["書類の種類"]; head = [c.value for c in ws[1]]; col = head.index("状態")
    for row in ws.iter_rows(min_row=2):
        if row[0].value == sys.argv[3]: row[col].value = "廃止" if cmd == "retire" else "使わない"
elif cmd == "skip":
    for row in wb["書類一覧"].iter_rows(min_row=2):
        if row[0].value == sys.argv[3]: row[5].value = "書かない"; row[6].value = "要らない"
wb.save(p)
PY
}
row() { grep -E "^\| $1 " "$md"; }

edit func "予約登録|予約入力||||"
edit func "振込データ取込||J110|IF-11||"
mkdir -p "$w/db/schema"; echo "CREATE TABLE TRANSFER_IMPORT (ID CHAR(1)\n);" > "$w/db/schema/TRANSFER_IMPORT.sql"
run list
row "S-22-001" | grep -q '予約登録' && row "S-22-002" | grep -q '振込データ取込' && ok || ng "機能ごとに処理設計書ができる"
row "S-23-001" | grep -q 'J110 | S-22-002' && ok || ng "ジョブ設計書の機能は、そのジョブを使う処理設計書"
row "S-21-001" | grep -q '予約入力 | S-22-001' && ok || ng "役割が機能の中心でない書類（画面設計書）は、機能の処理設計書に属する"
row "S-16-001" | grep -q 'TRANSFER_IMPORT |  |' && ok || ng "テーブル設計書は DDL のファイルごとにでき、機能を持たない"
row "S-11-001" | grep -q '方式設計書' && ok || ng "システムに1つの書類は自動で並ぶ"
row "S-20-001" | grep -q 'データモデル設計書' && ok || ng "データモデル設計書が並ぶ"
[ -z "$(row 'S-10-001')" ] && ok || ng "状態が廃止の書類の種類は並ばない"
edit skip "S-33-001"
edit func "ツアー検索|ツアー検索||||"
echo "CREATE TABLE TOURINFO (ID CHAR(1)\n);" > "$w/db/schema/TOURINFO.sql"
edit delfunc "予約登録"
run list
row "S-22-002" | grep -q '振込データ取込' && row "S-22-003" | grep -q 'ツアー検索' && ok || ng "番号は保たれ、新しい機能は末尾の番号"
row "S-22-001" | grep -q '廃止' && ok || ng "機能一覧から外れた書類は消さずに廃止"
row "S-33-001" | grep -q '書かない | 要らない' && ok || ng "人が付けた「書かない」と理由は残る"
row "S-16-002" | grep -q 'TOURINFO' && ok || ng "DDL を足すとテーブル設計書が末尾の番号で増える"
rm "$w/db/schema/TRANSFER_IMPORT.sql"; run list
row "S-16-001" | grep -q '廃止 | DDL（db/schema）から外れた' && ok || ng "DDL を消したテーブルの設計書は消さずに廃止"
edit retire "S-31"
run list
row "S-31-001" | grep -q '廃止 | 書類の種類を廃止した' && ok || ng "書類の種類を廃止すると、その書類は消さずに廃止"
edit unused S-18
run list
row "S-18-001" | grep -q '廃止 | この案件では使わない書類の種類にした' && ok || ng "案件で使わないにした書類の種類は、書類一覧で廃止になる"
run scaffold
f="$w/docs/design/S-23-001_J110.md"
[ -f "$f" ] && grep -q '^## D-08002 起動条件' "$f" && ok || ng "ひな形に記載項目の見出しが並ぶ"
[ ! -e "$w/docs/design/S-33-001_移行設計書.md" ] && [ ! -e "$w/docs/design/S-22-001_予約登録.md" ] && ok || ng "書かない・廃止の書類はひな形を作らない"
run export --check && ok || ng "list・scaffold の後は書き出しが Excel と一致"
edit func "予約照会|予約照会||||"
run export --check && ng "Excel だけ直すと書き出しと食い違う" || ok
# 誰が埋める列かを色で示す（list で作り直しても消えない）
colors=$(python3 - "$w/docs/design/ID設計.xlsx" <<'PY'
import sys, openpyxl
wb = openpyxl.load_workbook(sys.argv[1])
ws = wb["書類一覧"]
head = {c.value: c.fill.fgColor.rgb for c in ws[1]}
print(wb.sheetnames[0], head["書類実体ID"], head["作成"], ws.cell(ws.max_row, 6).fill.fgColor.rgb,
      wb["機能一覧"].cell(1, 1).fill.fgColor.rgb, wb["振り分け表"].cell(1, 1).fill.fgColor.rgb)
PY
)
# 色は不透明（先頭 FF）で書く。00 だと透明として表示するビューアーがある
[ "$colors" = "凡例 FFEDEDED FFFFF2CC FFFFF2CC FFFFF2CC FFDDEBF7" ] && ok || ng "列の色（ツールは灰、人は黄、型は青）と凡例のシート: $colors"

rm -rf "$w"

echo "id-design: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
