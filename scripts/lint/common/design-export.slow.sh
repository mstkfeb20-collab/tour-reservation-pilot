#!/usr/bin/env bash
# ID 設計の原本（docs/design/ID設計.xlsx）と書き出し（ID設計.md）が食い違っていないかを確かめる（COMMON-009）。
# Excel を読むので openpyxl が要る。開発中の hooks（--fast）では動かさず、CI で確かめる。
source "$(dirname "$0")/../lib.sh"

[ -f "$TAZUNA_ROOT/docs/design/ID設計.xlsx" ] || lint_finish
if ! python3 -c 'import openpyxl' 2>/dev/null; then
  lint_error "COMMON-009" "docs/design/ID設計.xlsx" \
    "Excel を読むための openpyxl がありません" \
    "原本の Excel と書き出しが食い違っていないかを確かめられません" \
    "pip install openpyxl を実行してください（CI では verify.yml で入れています）" \
    "scripts/design/catalog.py"
  lint_finish
fi
TAZUNA_ROOT="$TAZUNA_ROOT" python3 "$TAZUNA_ROOT/scripts/design/id_design.py" export --check || TAZUNA_LINT_ERRORS=1
lint_finish
