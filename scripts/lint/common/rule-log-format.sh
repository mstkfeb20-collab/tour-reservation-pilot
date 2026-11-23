#!/usr/bin/env bash
# harness/rule-log.md の「防ぐ層」列を決められた値にそろえ、月次で集計できるようにする。
source "$(dirname "$0")/../lib.sh"

file="$TAZUNA_ROOT/harness/rule-log.md"
[ -f "$file" ] || lint_finish

n=0
while IFS= read -r line; do
  n=$((n + 1))
  # 表の行のうち、日付で始まるものだけを対象にする
  [[ "$line" =~ ^\|[[:space:]]*[0-9]{4}-[0-9]{2}-[0-9]{2} ]] || continue
  layer=$(echo "$line" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $5); print $5}')
  if ! [[ "$layer" =~ ^(設計|Lint|テスト|実行検証|文章|hooks)$ ]]; then
    lint_error "COMMON-005" "harness/rule-log.md:$n" \
      "防ぐ層 '$layer' は使えない値です" \
      "層の名前がそろっていないと、metrics.md で『文章の割合』を集計できません" \
      "設計・Lint・テスト・実行検証・文章・hooks のどれかにしてください" \
      "harness/GUIDE.md#ミスが起きたとき"
  fi
done < "$file"
lint_finish
