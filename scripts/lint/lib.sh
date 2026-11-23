#!/usr/bin/env bash
# tazuna lint 共通ライブラリ
# すべてのチェックは、エージェントが自分で直せるように
# 「何がダメか・なぜダメか・どう直すか・参照先」を必ず出力する。

# リポジトリのルート
TAZUNA_ROOT="${TAZUNA_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
export TAZUNA_ROOT

TAZUNA_LINT_ERRORS=0

# lint_error <ルールID> <場所> <内容> <理由> <修正> <参照>
lint_error() {
  local rule="$1" where="$2" what="$3" why="$4" fix="$5" ref="$6"
  TAZUNA_LINT_ERRORS=$((TAZUNA_LINT_ERRORS + 1))
  {
    echo "ERROR [${rule}] ${where}"
    echo "  内容: ${what}"
    echo "  理由: ${why}"
    echo "  修正: ${fix}"
    echo "  参照: ${ref}"
  } >&2
}

# lint_warn <ルールID> <場所> <内容>
lint_warn() {
  echo "WARN  [$1] $2 : $3" >&2
}

# チェックの最後に呼ぶ。エラーがあれば終了コード1。
lint_finish() {
  if [ "${TAZUNA_LINT_ERRORS}" -gt 0 ]; then
    exit 1
  fi
  exit 0
}
