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
elif cmd == "skip":
    for row in wb["書類一覧"].iter_rows(min_row=2):
        if row[0].value == sys.argv[3]: row[5].value = "書かない"; row[6].value = "要らない"
wb.save(p)
PY
}
row() { grep -E "^\| $1 " "$md"; }

edit func "予約登録|予約入力|||||"
edit func "振込データ取込||J110|IF-11||TRANSFER_IMPORT|"
run list
row "S-22-001" | grep -q '予約登録' && row "S-22-002" | grep -q '振込データ取込' && ok || ng "機能ごとに処理設計書ができる"
row "S-23-001" | grep -q 'J110 | S-22-002' && ok || ng "ジョブ設計書の機能は、そのジョブを使う処理設計書"
row "S-16-001" | grep -q 'TRANSFER_IMPORT |  |' && ok || ng "テーブル定義書は機能を持たない"
row "S-11-001" | grep -q '方式設計書' && ok || ng "システムに1つの書類は自動で並ぶ"
edit skip "S-33-001"
edit func "ツアー検索|ツアー検索||||TOURINFO|"
edit delfunc "予約登録"
run list
row "S-22-002" | grep -q '振込データ取込' && row "S-22-003" | grep -q 'ツアー検索' && ok || ng "番号は保たれ、新しい機能は末尾の番号"
row "S-22-001" | grep -q '廃止' && ok || ng "機能一覧から外れた書類は消さずに廃止"
row "S-33-001" | grep -q '書かない | 要らない' && ok || ng "人が付けた「書かない」と理由は残る"
run scaffold
f="$w/docs/design/S-23-001_J110.md"
[ -f "$f" ] && grep -q '^## D-08002 起動条件' "$f" && ok || ng "ひな形に記載項目の見出しが並ぶ"
[ ! -e "$w/docs/design/S-33-001_移行設計書.md" ] && [ ! -e "$w/docs/design/S-22-001_予約登録.md" ] && ok || ng "書かない・廃止の書類はひな形を作らない"
run export --check && ok || ng "list・scaffold の後は書き出しが Excel と一致"
edit func "予約照会|予約照会|||||"
run export --check && ng "Excel だけ直すと書き出しと食い違う" || ok
rm -rf "$w"

echo "id-design: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
