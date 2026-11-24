#!/usr/bin/env bash
# scripts/report/report.py の自己テスト。一時的な git リポジトリで PR 単位と日次のレポートを作り、数え方を確かめる。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; PY="$ROOT/scripts/report/report.py"; pass=0; fail=0
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
check() { if grep -qF -- "$2" <<<"$3"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: $1（「$2」がない）"; echo "$3" | sed 's/^/    /'; fi; }
g() { git -C "$w" -c user.email=t@t -c user.name=t "$@"; }

mkdir -p "$w/docs/requirements" "$w/docs/tasks" "$w/src/test" "$w/.github/hooks"
g init -q; g checkout -q -b develop
printf 'docs/requirements/*\n' > "$w/.github/hooks/protected-paths.txt"
cat > "$w/docs/requirements/a.md" <<'MD'
## REQ-22001 予約取消

- 完了条件:
  - 取り消せる

## テスト仕様：予約取消（S-26-001）

- 前日は取り消せる（S-26-001/D-15001/1・テスト観点・ケース）
- 当日は取り消せない（S-26-001/D-15001/2・テスト観点・ケース）
- 実機で確かめる（S-26-001/D-15008/1・実機確認）

### 実装するときの条件（S-26-001）

- 本物のデータは使わない（S-26-001/D-15002/1・テストデータ）
MD
g add -A; g commit -qm base
echo '@Tag("REQ-22001") @Tag("S-26-001/D-15001/1")' > "$w/src/test/ATest.java"
echo x >> "$w/docs/requirements/a.md"
g add -A; g commit -qm feature
body=$'対象要件: REQ-22001\n\n未対応: S-26-001/D-15008/1（銀行のテスト環境が用意できない）\n> 未対応: S-26-001/D-15001/2（引用は数えない）'
out=$(TAZUNA_ROOT="$w" python3 "$PY" pr --base HEAD~1 --body-file <(printf '%s' "$body") --lint ok)
check "テスト仕様の行を数える（### の下は数えない）" "テストで確かめた 1 ・ 未対応と書いた 1 ・ **どちらでもない 1** （全 3 行）" "$out"
check "どちらでもない行を出す" "- [ ] S-26-001/D-15001/2 当日は取り消せない" "$out"
check "未対応の理由を出す" "- 未対応 S-26-001/D-15008/1: 銀行のテスト環境が用意できない" "$out"
check "保護ファイルの変更を出す" "保護ファイルの変更: **docs/requirements/a.md**" "$out"
out=$(TAZUNA_ROOT="$w" python3 "$PY" pr --base HEAD~1 --body-file <(printf '対象要件: なし') )
check "対象要件なし" "対象要件: なし" "$out"
out=$(TAZUNA_ROOT="$w" python3 "$PY" daily --branch develop --since "2000-01-01")
check "日次: 新しい要件" "新しく決まった要件: REQ-22001" "$out"
check "日次: テストありになった要件" "テストありになった要件: REQ-22001" "$out"
out=$(TAZUNA_ROOT="$w" python3 "$PY" daily --branch nothing)
check "日次: ないブランチ" "ブランチ nothing がありません" "$out"
[ -z "$(git -C "$w" worktree list | sed 1d)" ] && pass=$((pass + 1)) || { fail=$((fail + 1)); echo "NG: 前日のツリーを片付ける"; }

echo "report: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
