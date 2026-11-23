#!/usr/bin/env bash
# .github/hooks/*.json が Copilot の hooks 形式として正しいかを確かめる。
source "$(dirname "$0")/../lib.sh"

dir="$TAZUNA_ROOT/.github/hooks"
[ -d "$dir" ] || lint_finish

if ! command -v jq >/dev/null 2>&1; then
  lint_warn "COMMON-006" ".github/hooks" "jq がないため hooks 設定の検証をスキップしました"
  lint_finish
fi

for f in "$dir"/*.json; do
  [ -f "$f" ] || continue
  rel=".github/hooks/$(basename "$f")"
  if ! jq -e . "$f" >/dev/null 2>&1; then
    lint_error "COMMON-006" "$rel" \
      "JSON として読み込めません" \
      "壊れた hooks 設定は黙って無視され、危険な操作が止まらなくなります" \
      "jq . $rel でエラー箇所を確認して直してください" \
      "https://docs.github.com/en/copilot/reference/hooks-reference"
    continue
  fi
  if [ "$(jq -r '.version' "$f")" != "1" ]; then
    lint_error "COMMON-006" "$rel" \
      "version が 1 ではありません" \
      "Copilot は version: 1 の hooks 設定しか読み込みません" \
      "最上位に \"version\": 1 を指定してください" \
      "https://docs.github.com/en/copilot/reference/hooks-reference"
  fi
  # bash で呼んでいるスクリプトが存在するか
  while IFS= read -r cmd; do
    script=$(echo "$cmd" | grep -oE '\.github/hooks/scripts/[A-Za-z0-9_.-]+' | head -1)
    if [ -n "$script" ] && [ ! -f "$TAZUNA_ROOT/$script" ]; then
      lint_error "COMMON-006" "$rel" \
        "呼び出し先 $script が存在しません" \
        "スクリプトがないと hooks が失敗し、ガードが効きません" \
        "パスを直すか、スクリプトを作成してください" \
        ".github/hooks/scripts/"
    fi
  done < <(jq -r '.hooks[][]?.bash // empty' "$f")
done
lint_finish
