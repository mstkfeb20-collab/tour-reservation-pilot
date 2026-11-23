#!/usr/bin/env bash
# postToolUse: ファイルを書き換えた直後に高速なLintを走らせ、結果をエージェントに返す。
# 判定ロジックはここに書かない（scripts/lint/ を呼ぶだけ）。
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
payload="$(cat)"

command -v jq >/dev/null 2>&1 || { echo '{}'; exit 0; }

tool=$(jq -r '.toolName // .tool_name // ""' <<< "$payload")
case "$tool" in
  edit|create|write|str_replace|str_replace_editor|apply_patch|insert|Edit|Write|MultiEdit) ;;
  *) echo '{}'; exit 0 ;;
esac

if out=$(bash "$ROOT/scripts/lint/run-all.sh" --fast 2>&1); then
  echo '{}'
else
  # 10KB の上限に収まるよう末尾を切り詰める
  msg="Lint が失敗しました。次のエラーを直してから作業を続けてください。
$(printf '%s' "$out" | tail -c 8000)"
  jq -cn --arg c "$msg" '{additionalContext: $c}'
fi
exit 0
