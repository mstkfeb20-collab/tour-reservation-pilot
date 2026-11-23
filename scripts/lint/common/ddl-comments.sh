#!/usr/bin/env bash
# DDL（db/schema/*.sql）がテーブル・列の説明を持ち、区分値の列が値の意味を決めた設計書の行を指すかを確かめる（COMMON-010）。
# db/schema/ がない案件では何もしない。
source "$(dirname "$0")/../lib.sh"

[ -d "$TAZUNA_ROOT/db/schema" ] || lint_finish
python3 "$TAZUNA_ROOT/scripts/lint/common/ddl_comments.py" "$TAZUNA_ROOT" || TAZUNA_LINT_ERRORS=1
lint_finish
