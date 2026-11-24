#!/usr/bin/env bash
# hooks の自己テスト。CI で実行し、ガードが効いていることを確かめる。
#   bash .github/hooks/tests/test-guard.sh
set -u
cd "$(dirname "$0")/../../.." || exit 2

GUARD=".github/hooks/scripts/guard.sh"
fail=0

# expect <deny|allow> <説明> <payload>
expect() {
  local want="$1" name="$2" payload="$3" got
  got=$(printf '%s' "$payload" | bash "$GUARD" | jq -r '.permissionDecision // "allow"' 2>/dev/null)
  [ -z "$got" ] && got="allow"
  if [ "$got" = "$want" ]; then
    echo "ok   - $name"
  else
    echo "FAIL - $name（期待: $want / 結果: $got）"
    fail=1
  fi
}

bash_cmd() { jq -cn --arg c "$1" '{toolName: "bash", toolArgs: {command: $c}}'; }
edit_path() { jq -cn --arg p "$1" '{toolName: "edit", toolArgs: {path: $p}}'; }

# --- 危険なコマンド ---
expect deny  "強制pushを止める"            "$(bash_cmd 'git push --force origin main')"
expect deny  "-f の強制pushを止める"        "$(bash_cmd 'git push -f')"
expect deny  "--no-verify を止める"        "$(bash_cmd 'git commit --no-verify -m x')"
expect deny  "テスト削除を止める"           "$(bash_cmd 'rm -rf src/test/java/com/example')"
expect deny  "reset --hard を止める"       "$(bash_cmd 'git reset --hard HEAD~1')"
expect allow "通常のpushは通す"             "$(bash_cmd 'git push origin feature/x')"
expect allow "テスト実行は通す"             "$(bash_cmd 'mvn -B verify')"
expect deny  "toolArgs が文字列でも読める"  '{"toolName":"bash","toolArgs":"{\"command\":\"git push --force\"}"}'

# --- 守るべきファイル（_tazuna/ がない案件リポジトリを想定）---
if [ -d _tazuna ]; then
  mv _tazuna _tazuna.bak
  trap 'mv _tazuna.bak _tazuna' EXIT
fi
expect deny  "base スキルの編集を止める"     "$(edit_path '.github/skills/base-code-review/SKILL.md')"
expect deny  "不変条件の編集を止める"        "$(edit_path 'docs/domain/invariants.md')"
expect deny  "共通Lintの編集を止める"        "$(edit_path 'scripts/lint/common/skill-naming.sh')"
expect deny  "絶対パスでも止める"            "$(edit_path "$PWD/docs/requirements/README.md")"
expect deny  "ID 設計の原本（Excel）の編集を止める" "$(edit_path 'docs/design/ID設計.xlsx')"
expect allow "ID 設計書の編集は通す"            "$(edit_path 'docs/design/S-22-001_予約登録.md')"
expect deny  "シェル経由の書き換えも止める"   "$(bash_cmd 'sed -i s/a/b/ docs/domain/invariants.md')"
expect allow "proj スキルは編集できる"       "$(edit_path '.github/skills/proj-example-reservation/SKILL.md')"
expect allow "業務固有Lintは編集できる"      "$(edit_path 'scripts/lint/domain/java-money-no-float.sh')"
expect allow "プロダクトコードは編集できる"   "$(edit_path 'src/main/java/com/example/domain/Money.java')"
patch_of() { jq -cn --arg p "$1" '{toolName: "apply_patch", toolArgs: {input: $p}}'; }
expect deny  "apply_patch での要件の編集を止める" "$(patch_of $'*** Begin Patch\n*** Update File: docs/requirements/README.md\n@@\n-a\n+b\n*** End Patch')"
expect deny  "apply_patch で保護ファイルへ移すのを止める" "$(patch_of $'*** Begin Patch\n*** Update File: src/main/java/A.java\n*** Move to: docs/domain/invariants.md\n*** End Patch')"
expect deny  "apply_patch（unified diff）でも止める" "$(patch_of $'--- a/scripts/lint/common/skill-naming.sh\n+++ b/scripts/lint/common/skill-naming.sh\n@@ -1 +1 @@\n-a\n+b')"
expect deny  "toolArgs が文字列の apply_patch でも止める" "$(jq -cn --arg p $'*** Begin Patch\n*** Add File: docs/requirements/x.md\n+a\n*** End Patch' '{toolName: "apply_patch", toolArgs: ({input: $p} | tostring)}')"
expect deny  "toolArgs がパッチ本文そのもの（JSON でない）でも止める" "$(jq -cn --arg p $'*** Begin Patch\n*** Update File: docs/requirements/README.md\n@@\n-a\n+b\n*** End Patch' '{toolName: "apply_patch", toolArgs: $p}')"
expect allow "apply_patch でのプロダクトコードの編集は通す" "$(patch_of $'*** Begin Patch\n*** Update File: src/main/java/com/example/domain/Money.java\n@@\n-a\n+b\n*** End Patch')"
expect allow "保護ファイルの閲覧は通す"      "$(bash_cmd 'cat docs/domain/invariants.md')"

exit $fail
