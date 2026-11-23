#!/usr/bin/env bash
# skills は base-*（普遍）と proj-*（ドメイン特有）に分ける。
source "$(dirname "$0")/../lib.sh"

dir="$TAZUNA_ROOT/.github/skills"
[ -d "$dir" ] || lint_finish

for skill in "$dir"/*/; do
  [ -d "$skill" ] || continue
  name=$(basename "$skill")
  rel=".github/skills/$name"

  if ! [[ "$name" =~ ^(base|proj)-[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
    lint_error "COMMON-002" "$rel" \
      "スキル名 '$name' が命名規則に合っていません" \
      "接頭辞で普遍（base-）とドメイン特有（proj-）を区別し、承認者を CODEOWNERS で分けるためです" \
      "base-<名前> または proj-<名前> に改名してください（小文字・ハイフン区切り）" \
      "harness/GUIDE.md#skillsの命名"
    continue
  fi

  md="$skill/SKILL.md"
  if [ ! -f "$md" ]; then
    lint_error "COMMON-002" "$rel" \
      "SKILL.md がありません" \
      "エージェントはスキルのディレクトリ内の SKILL.md だけを読み込みます" \
      "$rel/SKILL.md を作成してください" \
      ".github/skills/base-code-review/SKILL.md（例）"
    continue
  fi

  fm_name=$(awk '/^---/{n++; next} n==1 && /^name:/{sub(/^name:[ ]*/,""); print; exit}' "$md")
  fm_desc=$(awk '/^---/{n++; next} n==1 && /^description:/{sub(/^description:[ ]*/,""); print; exit}' "$md")

  if [ "$fm_name" != "$name" ]; then
    lint_error "COMMON-002" "$rel/SKILL.md" \
      "frontmatter の name ('$fm_name') がディレクトリ名 ('$name') と一致しません" \
      "名前が食い違うと、エージェントが呼び出すスキルとファイルの対応が分からなくなります" \
      "frontmatter を name: $name にしてください" \
      "harness/GUIDE.md#skillsの命名"
  fi
  if [ -z "$fm_desc" ]; then
    lint_error "COMMON-002" "$rel/SKILL.md" \
      "frontmatter に description がありません" \
      "エージェントは description を見て、いつこのスキルを使うかを判断します" \
      "description: に『いつ使うか』を1文で書いてください" \
      "harness/GUIDE.md#skillsの命名"
  fi
done
lint_finish
