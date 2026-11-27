#!/usr/bin/env bash
# 設計書の点検（スキル base-design-review）が済み、人のレビューを始めてよいかを確かめる（COMMON-011）。
# 中身は scripts/design/review_record.py。止めるのは、設計書を変えた PR（ドラフトを除く）だけ。手元では警告にする。
source "$(dirname "$0")/../lib.sh"

[ -d "$TAZUNA_ROOT/docs/design" ] || lint_finish
TAZUNA_ROOT="$TAZUNA_ROOT" python3 "$TAZUNA_ROOT/scripts/design/review_record.py" check || TAZUNA_LINT_ERRORS=1
lint_finish
