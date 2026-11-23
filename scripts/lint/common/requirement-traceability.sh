#!/usr/bin/env bash
# 要件ID（REQ-xxx）・テスト仕様・テストの対応を、進め方の段階に合わせて確かめる（COMMON-003）。
#   ② 要件を決める PR: 要件には完了条件があり、要件を書いたファイルにはテスト仕様（## テスト仕様）がある
#   ③④ 実装の PR: PR の「対象要件」に挙げた要件には、それを確かめるテストがある
#   いつでも: テストが参照する要件IDは、docs/requirements/ に定義されている
# テストのまだない要件は、エラーにしない（進捗で「未実装」と出る。python3 scripts/design/id_design.py progress）。
# 要件の定義は見出し「## REQ-001 タイトル」、テストからの参照はテストコード中の REQ-001（例: @Tag("REQ-001")）。
# 対象要件は、PR の本文の「対象要件: REQ-001, REQ-002」の行（CI では TAZUNA_PR_BODY に PR の本文が入る）か、TAZUNA_TARGET_REQS。
source "$(dirname "$0")/../lib.sh"

REQ_DIR="$TAZUNA_ROOT/docs/requirements"
TEST_DIRS="${TAZUNA_TEST_DIRS:-src/test tests}"

[ -d "$REQ_DIR" ] || lint_finish

defined=$(grep -rhoE '^##[[:space:]]+REQ-[0-9]+' "$REQ_DIR" 2>/dev/null | grep -oE 'REQ-[0-9]+' | sort -u)

referenced=""
for d in $TEST_DIRS; do
  [ -d "$TAZUNA_ROOT/$d" ] || continue
  referenced+=$'\n'$(grep -rhoE 'REQ-[0-9]+' "$TAZUNA_ROOT/$d" 2>/dev/null)
done
referenced=$(echo "$referenced" | grep -E 'REQ-' | sort -u)

# ② 要件ごとの完了条件と、ファイルごとのテスト仕様
for f in "$REQ_DIR"/*.md; do
  [ -e "$f" ] || continue
  rel="docs/requirements/$(basename "$f")"
  grep -qE '^##[[:space:]]+REQ-[0-9]+' "$f" || continue
  if ! grep -qE '^##[[:space:]]+テスト仕様' "$f"; then
    lint_error "COMMON-003" "$rel" \
      "要件はあるのに、テスト仕様（## テスト仕様）がありません" \
      "要件を決めるときに『何で確かめるか』も決めておかないと、実装の後でテストが要件からずれます" \
      "テスト仕様書（S-26）を書いて転記するか、要件ファイルに「## テスト仕様」の節を書いてください" \
      "docs/requirements/README.md"
  fi
  awk '/^## /{ if (id != "" && n == 0) print id; id = ""; n = 0; if ($0 ~ /^##[[:space:]]+REQ-[0-9]+/) { match($0, /REQ-[0-9]+/); id = substr($0, RSTART, RLENGTH); inreq = 0 } next }
       id != "" && /完了条件/ { inreq = 1; next }
       id != "" && inreq && /^[[:space:]]+- / { n++ }
       END { if (id != "" && n == 0) print id }' "$f" | while read -r id; do
    lint_error "COMMON-003" "$rel ($id)" \
      "要件 $id に完了条件がありません" \
      "完了条件がないと、何ができたら終わりかを誰も判断できません" \
      "設計書に完了条件になる行を書いて転記するか、「- 完了条件:」の下に条件を書いてください" \
      "docs/requirements/README.md"
  done
done

# いつでも: テストが参照する要件が定義されている
for id in $referenced; do
  if ! grep -qx "$id" <<< "$defined"; then
    lint_error "COMMON-003" "テストコード ($id)" \
      "テストが参照する $id が docs/requirements/ に定義されていません" \
      "要件の正本にない ID は、削除された要件か誤記です。テストが何を保証しているか追えなくなります" \
      "docs/requirements/ に '## $id' を定義するか、テストの ID を正しいものに直してください" \
      "docs/requirements/README.md"
  fi
done

# ③④ 実装の PR: 対象要件にテストがある
# CI の PR では TAZUNA_IS_PR=1。本文に「対象要件:」の行がなければエラー（「対象要件: なし」は可）。
# 行がないまま通すと、対象要件の検査をしないまま CI が成功してしまう（引用「> 対象要件:」も行とは見なさない）
targets="${TAZUNA_TARGET_REQS:-}"
if [ -z "$targets" ] && { [ -n "${TAZUNA_PR_BODY:-}" ] || [ "${TAZUNA_IS_PR:-}" = "1" ]; }; then
  line=$(grep -E '^[[:space:]]*対象要件[:：]' <<< "${TAZUNA_PR_BODY:-}")
  if [ -z "$line" ] && [ "${TAZUNA_IS_PR:-}" = "1" ]; then
    lint_error "COMMON-003" "PR の本文" \
      "PR の本文に「対象要件:」の行がありません" \
      "対象要件がないと、この PR で実装した要件にテストがあるかを確かめられないまま CI が通ります" \
      "本文に「対象要件: REQ-22001, REQ-23001」の行を書いてください（要件を実装しない PR は「対象要件: なし」）。本文を直すと CI がやり直されます" \
      ".github/pull_request_template.md"
  fi
  targets=$(grep -oE 'REQ-[0-9]+' <<< "$line" | tr '\n' ' ')
fi
for id in $targets; do
  if ! grep -qx "$id" <<< "$defined"; then
    lint_error "COMMON-003" "PR の対象要件 ($id)" \
      "対象要件 $id が docs/requirements/ に定義されていません" \
      "決まっていない要件を実装すると、何を確かめたのか追えません" \
      "要件を先に転記して決めるか、対象要件の ID を直してください" \
      "docs/requirements/README.md"
  elif ! grep -qx "$id" <<< "$referenced"; then
    lint_error "COMMON-003" "PR の対象要件 ($id)" \
      "対象要件 $id を確かめるテストがありません" \
      "この PR で実装した要件は、テストで確かめられないと『終わった』と判断できません" \
      "要件のテスト仕様からテストを作り、@Tag(\"$id\") を付けてください" \
      ".github/skills/base-test-design/SKILL.md"
  fi
done
lint_finish
