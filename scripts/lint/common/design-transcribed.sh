#!/usr/bin/env bash
# ID 設計書（docs/design/）と、転記先（要件・候補・作業一覧など）が食い違っていないかを確かめる（COMMON-008）。
# 設計書を直したら scripts/design/transcribe.py で転記し直す。docs/design/ がない案件では何もしない。
source "$(dirname "$0")/../lib.sh"

[ -d "$TAZUNA_ROOT/docs/design" ] || lint_finish
TAZUNA_ROOT="$TAZUNA_ROOT" python3 "$TAZUNA_ROOT/scripts/design/transcribe.py" --check || TAZUNA_LINT_ERRORS=1
lint_finish
