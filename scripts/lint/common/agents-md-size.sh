#!/usr/bin/env bash
# AGENTS.md は常時読み込まれる索引なので、短く保つ。
source "$(dirname "$0")/../lib.sh"

MAX_LINES="${AGENTS_MD_MAX_LINES:-60}"
file="$TAZUNA_ROOT/AGENTS.md"

if [ ! -f "$file" ]; then
  lint_error "COMMON-001" "AGENTS.md" \
    "AGENTS.md がありません" \
    "エージェントが最初に読む索引がないと、原則・コマンド・参照先が伝わりません" \
    "ルートに AGENTS.md を作成してください（ひな形は tazuna の AGENTS.md）" \
    "harness/GUIDE.md#置き場所の判断基準"
  lint_finish
fi

lines=$(wc -l < "$file")
if [ "$lines" -gt "$MAX_LINES" ]; then
  lint_error "COMMON-001" "AGENTS.md" \
    "AGENTS.md が ${lines} 行あります（上限 ${MAX_LINES} 行）" \
    "常時読み込まれるため、長いとすべての作業の文脈を圧迫し、重要な原則が埋もれます" \
    "詳細な手順は .github/skills/ へ、業務知識は docs/ へ移し、AGENTS.md には索引だけを残してください" \
    "harness/GUIDE.md#月次の見直し"
fi
lint_finish
