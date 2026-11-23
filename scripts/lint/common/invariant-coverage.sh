#!/usr/bin/env bash
# 業務の不変条件（INV-xxx）ごとに「どの層で防ぐか」と「担保している仕組み」を明記させる。
#   ## INV-001 タイトル
#   - 防ぐ層: 設計 | Lint | テスト | 実行検証 | 文章
#   - 担保: <ファイルパス>（防ぐ層が「文章」以外のとき必須）
source "$(dirname "$0")/../lib.sh"

file="$TAZUNA_ROOT/docs/domain/invariants.md"
[ -f "$file" ] || lint_finish

current=""
layer=""
guard=""

check_section() {
  [ -z "$current" ] && return
  if [ -z "$layer" ]; then
    lint_error "COMMON-004" "docs/domain/invariants.md ($current)" \
      "$current に『防ぐ層』がありません" \
      "どの層で守るかが決まっていない不変条件は、文章だけで守られ、エージェントに無視されやすくなります" \
      "'- 防ぐ層: 設計|Lint|テスト|実行検証|文章' の行を追加してください" \
      "harness/GUIDE.md#ルールは破れない場所から守る"
  elif ! [[ "$layer" =~ ^(設計|Lint|テスト|実行検証|文章)$ ]]; then
    lint_error "COMMON-004" "docs/domain/invariants.md ($current)" \
      "防ぐ層 '$layer' は使えない値です" \
      "層の名前をそろえないと、月次の集計ができません" \
      "設計・Lint・テスト・実行検証・文章 のどれかにしてください" \
      "harness/GUIDE.md#ルールは破れない場所から守る"
  elif [ "$layer" = "文章" ]; then
    lint_warn "COMMON-004" "docs/domain/invariants.md ($current)" "文章でしか守られていません。設計・Lint・テストで防げないか検討してください"
  else
    if [ -z "$guard" ]; then
      lint_error "COMMON-004" "docs/domain/invariants.md ($current)" \
        "$current に『担保』がありません" \
        "防ぐ層を宣言しても、実際の仕組みがなければ守られません" \
        "'- 担保: <Lintスクリプトやテストのパス>' を追加してください" \
        "docs/domain/invariants.md の INV-001（例）"
    else
      for p in $guard; do
        p="${p%%#*}"
        if [ ! -e "$TAZUNA_ROOT/$p" ]; then
          lint_error "COMMON-004" "docs/domain/invariants.md ($current)" \
            "担保に書かれた $p が存在しません" \
            "仕組みが削除・移動されると、不変条件が守られていない状態に気づけません" \
            "パスを正しく直すか、担保する仕組みを作り直してください" \
            "docs/domain/invariants.md"
        fi
      done
    fi
  fi
}

while IFS= read -r line; do
  if [[ "$line" =~ ^##[[:space:]]+(INV-[0-9]+) ]]; then
    next="${BASH_REMATCH[1]}"   # check_section 内の =~ で BASH_REMATCH が上書きされるため先に退避
    check_section
    current="$next"; layer=""; guard=""
  elif [[ "$line" =~ ^-[[:space:]]*防ぐ層:[[:space:]]*(.*)$ ]]; then
    layer="$(echo "${BASH_REMATCH[1]}" | xargs)"
  elif [[ "$line" =~ ^-[[:space:]]*担保:[[:space:]]*(.*)$ ]]; then
    guard="$(echo "${BASH_REMATCH[1]}" | tr -d '`' | tr ',、' '  ')"
  fi
done < "$file"
check_section
lint_finish
