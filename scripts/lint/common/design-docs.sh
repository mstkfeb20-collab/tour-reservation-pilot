#!/usr/bin/env bash
# ID 設計書（docs/design/）の置き場所と番号を検査する。docs/design/ がない案件では何もしない。
# 中身は design_docs.py。PR では DESIGN_BASE_REF に比較元（例 origin/main）を入れると、消えた行IDも検査する。
source "$(dirname "$0")/../lib.sh"

[ -d "$TAZUNA_ROOT/docs/design" ] || lint_finish

args=("$TAZUNA_ROOT/docs/design")
[ -n "${DESIGN_BASE_REF:-}" ] && args+=(--base "$DESIGN_BASE_REF")
python3 "$(dirname "$0")/design_docs.py" "${args[@]}" || TAZUNA_LINT_ERRORS=1
lint_finish
