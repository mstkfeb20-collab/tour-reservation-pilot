#!/usr/bin/env bash
# preToolUse: エージェントの「行為」を止める。
#   - 危険なコマンド       → .github/hooks/deny-commands.txt
#   - 守るべきファイルの編集 → .github/hooks/protected-paths.txt
# 止めるときは理由と代わりの方法を返し、エージェントが別の手段を選べるようにする。
# 成果物（コード）の中身は判定しない。それは scripts/lint/ の役割。
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HOOKS_DIR="$ROOT/.github/hooks"

payload="$(cat)"

deny() {
  jq -cn --arg r "$1" '{permissionDecision: "deny", permissionDecisionReason: $r}'
  exit 0
}

command -v jq >/dev/null 2>&1 || exit 0

tool=$(jq -r '.toolName // .tool_name // ""' <<< "$payload")
# toolArgs は JSON 文字列のこともあるので、オブジェクトにそろえる
# JSON でない文字列（apply_patch のパッチ本文そのものなど）は {input: 文字列} として扱う
args=$(jq -c '(.toolArgs // .tool_input // {}) | if type == "string" then (try fromjson catch {input: .}) else . end' <<< "$payload")

# 調べるとき: .git/tazuna-hook-debug を置くと、受け取った内容を .git/tazuna-hook-payloads.log に残す（コミットされない）
GIT_DIR_PATH="$(git rev-parse --git-dir 2>/dev/null || true)"
if [ -n "$GIT_DIR_PATH" ] && [ -f "$GIT_DIR_PATH/tazuna-hook-debug" ]; then
  printf '%s\n' "$payload" >> "$GIT_DIR_PATH/tazuna-hook-payloads.log"
fi

# --- 1. コマンドの確認 ---
cmd=$(jq -r '.command // .cmd // .script // empty' <<< "$args")
if [ -n "$cmd" ] && [ -f "$HOOKS_DIR/deny-commands.txt" ]; then
  while IFS=$'\t' read -r pattern reason; do
    [[ -z "$pattern" || "$pattern" == \#* ]] && continue
    if grep -qE -- "$pattern" <<< "$cmd"; then
      deny "このコマンドは禁止されています: ${reason}（ルール: .github/hooks/deny-commands.txt）"
    fi
  done < "$HOOKS_DIR/deny-commands.txt"
fi

# --- 2. 守るべきファイルの編集 ---
# tazuna 本体（_tazuna/ があるリポジトリ）では型の編集を許可する
[ -d "$ROOT/_tazuna" ] && exit 0
[ -f "$HOOKS_DIR/protected-paths.txt" ] || exit 0

is_write_tool=0
case "$tool" in
  edit|create|write|str_replace|str_replace_editor|apply_patch|insert|delete|Edit|Write|MultiEdit|NotebookEdit) is_write_tool=1 ;;
esac

paths=()
if [ "$is_write_tool" -eq 1 ]; then
  while IFS= read -r p; do paths+=("$p"); done < <(jq -r '[.. | objects | to_entries[] | select(.key | test("^(path|file_path|filePath|target|file)$")) | .value | strings] | .[]' <<< "$args")
  # apply_patch はパスを引数の項目ではなくパッチの本文に持つ（*** Update File: パス、+++ b/パス など）
  while IFS= read -r p; do [ -n "$p" ] && paths+=("$p"); done < <(
    { jq -r '[.. | strings] | .[]' <<< "$args"; jq -r '[.. | strings] | .[]' <<< "$payload"; } \
      | sed -nE 's/^\*\*\* (Add|Update|Delete) File: (.*)$/\2/p; s/^\*\*\* Move to: (.*)$/\1/p; s/^(\+\+\+|---) [ab]\/(.*)$/\2/p' \
      | sed -E 's/[[:space:]]+$//')
elif [ -n "$cmd" ]; then
  # シェル経由の書き込みだけを見る。書き込み先になる語だけを取り出す（読むだけ・実行するだけのコマンドは止めない）
  #   - リダイレクトの先（> ファイル、>> ファイル。2>&1 や /dev/null は除く）
  #   - 書き換えるコマンド（rm・mv・cp・tee・touch・truncate・sed -i・perl -i）の後ろの引数
  # コマンドは ; && || | で区切った1つずつで見る
  while IFS= read -r seg; do
    while IFS= read -r t; do
      [[ -n "$t" && "$t" != /dev/* ]] && paths+=("$t")
    done < <(grep -oE '[0-9]*>>?[[:space:]]*[^[:space:]&;|<>]+' <<< "$seg" | sed -E 's/^[0-9]*>>?[[:space:]]*//')
    read -r -a words <<< "$seg"
    i=0
    while [[ $i -lt ${#words[@]} && "${words[$i]}" == *=* ]]; do i=$((i + 1)); done  # 先頭の VAR=値 を飛ばす
    [[ "${words[$i]:-}" == sudo ]] && i=$((i + 1))
    verb="${words[$i]:-}"
    writes=0
    case "$verb" in
      rm|mv|cp|tee|touch|truncate|install) writes=1 ;;
      sed|perl) [[ " ${words[*]} " =~ [[:space:]]-i ]] && writes=1 ;;
    esac
    if [[ $writes -eq 1 ]]; then
      args_=()
      for ((j = i + 1; j < ${#words[@]}; j++)); do
        w="${words[$j]}"
        [[ "$w" == -* || "$w" == *'>'* ]] && continue
        args_+=("${w//[\'\"]/}")
      done
      # cp・install は最後の引数（書き込み先）だけ。読み元は書き換えない
      if [[ "$verb" == cp || "$verb" == install ]]; then
        [[ ${#args_[@]} -gt 0 ]] && paths+=("${args_[-1]}")
      else
        paths+=("${args_[@]}")
      fi
    fi
  done < <(sed -E 's/(\&\&|\|\||;|\|)/\n/g' <<< "$cmd")
fi

for raw in "${paths[@]}"; do
  p="${raw#"$ROOT"/}"
  p="${p#/workspace/}"
  p="${p#./}"
  while IFS= read -r pattern; do
    [[ -z "$pattern" || "$pattern" == \#* ]] && continue
    # shellcheck disable=SC2053
    if [[ "$p" == $pattern ]]; then
      deny "$p はエージェントが編集できないファイルです（パターン: $pattern）。変更が必要な場合は、変更案をPRの説明に書いて承認者に依頼してください。担当は .github/CODEOWNERS を参照"
    fi
  done < "$HOOKS_DIR/protected-paths.txt"
done

exit 0
