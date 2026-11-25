#!/usr/bin/env bash
# scripts/tazuna-update.sh（型の取り込み）の自己テスト。手元に tazuna と案件のリポジトリを作り、タグで取り込む。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; pass=0; fail=0
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
check() { if grep -qF -- "$2" <<<"$3"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: $1（「$2」がない）"; echo "$3" | sed 's/^/    /'; fi; }
ok() { if eval "$2"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: $1"; fi; }
g() { git -c user.name=t -c user.email=t@example.com -c init.defaultBranch=main "$@"; }

# tazuna（型）: v0.1.0 は古い一覧（ID 設計の Excel も型に載っている）
T="$w/tazuna"; mkdir -p "$T/docs/design" "$T/harness" "$T/scripts" "$T/_tazuna"; echo x > "$T/_tazuna/README.md"
cp "$ROOT/scripts/tazuna-update.sh" "$T/scripts/"
printf 'scripts/*\nharness/tazuna-paths.txt\ndocs/design/ID設計.xlsx\ndocs/design/ID設計.md\n' > "$T/harness/tazuna-paths.txt"
printf '# ID 設計\n\n## 機能一覧\n\n| 見本 |\n\n## 書類の種類\n\n| S-22 | 処理設計書 |\n' > "$T/docs/design/ID設計.md"
echo "xlsx v1" > "$T/docs/design/ID設計.xlsx"; echo "a" > "$T/scripts/tool.sh"; echo "v0.1.0" > "$T/harness/tazuna-version"
g -C "$T" init -q && g -C "$T" add -A && g -C "$T" commit -qm v1 && g -C "$T" tag v0.1.0

# 案件: v0.1.0 から作り、機能一覧と Excel を書く
P="$w/pj"; g clone -q "$T" "$P" 2>/dev/null; g -C "$P" rm -rq _tazuna
printf '# ID 設計\n\n## 機能一覧\n\n| 予約取消 |\n\n## 書類の種類\n\n| S-22 | 処理設計書 |\n' > "$P/docs/design/ID設計.md"
echo "xlsx 案件が書いた" > "$P/docs/design/ID設計.xlsx"
g -C "$P" add -A && g -C "$P" commit -qm pj

# v0.2.0: ツールが変わり、型は変わらない
echo "b" > "$T/scripts/tool.sh"; echo "xlsx v2" > "$T/docs/design/ID設計.xlsx"
g -C "$T" commit -qam v2 && g -C "$T" tag v0.2.0
out=$(cd "$P" && TAZUNA_REMOTE_URL="$T" bash scripts/tazuna-update.sh v0.2.0 2>&1)
ok "型のファイルは取り込む" '[ "$(cat "$P/scripts/tool.sh")" = b ]'
ok "案件の Excel は上書きしない" '[ "$(cat "$P/docs/design/ID設計.xlsx")" = "xlsx 案件が書いた" ]'
ok "案件の書き出しは上書きしない" 'grep -q 予約取消 "$P/docs/design/ID設計.md"'
check "型が変わっていなければそう伝える" "型（書類の種類・記載項目・設計項目）は変わっていません" "$out"
ok "型が変わっていなければ取り出さない" '[ ! -e "$P/.tazuna-download/ID設計-v0.2.0.xlsx" ]'
g -C "$P" commit -qam up

# v0.3.0: 型の行が増え、一覧から Excel を外す。日本語の名前の型のファイルも足す
printf 'scripts/*\nharness/tazuna-paths.txt\ntemplates/*\n' > "$T/harness/tazuna-paths.txt"
mkdir -p "$T/templates"; echo "bug" > "$T/templates/不具合.md"; g -C "$T" add -A
printf '# ID 設計\n\n## 機能一覧\n\n| 見本 |\n\n## 書類の種類\n\n| S-22 | 処理設計書 |\n| S-31 | テスト計画書 |\n' > "$T/docs/design/ID設計.md"
echo "xlsx v3" > "$T/docs/design/ID設計.xlsx"
g -C "$T" commit -qam v3 && g -C "$T" tag v0.3.0
out=$(cd "$P" && TAZUNA_REMOTE_URL="$T" bash scripts/tazuna-update.sh v0.3.0 2>&1)
ok "一覧から外した Excel を消さない" '[ "$(cat "$P/docs/design/ID設計.xlsx")" = "xlsx 案件が書いた" ]'
ok "型が変われば新しい Excel を取り出す" '[ "$(cat "$P/.tazuna-download/ID設計-v0.3.0.xlsx")" = "xlsx v3" ]'
ok "型の差分に増えた行が出る" 'grep -q "^+| S-31 | テスト計画書 |" "$P/.tazuna-download/ID設計の型の差分-v0.2.0-v0.3.0.diff"'
ok "差分に機能一覧は出ない" '! grep -q 見本 "$P/.tazuna-download/ID設計の型の差分-v0.2.0-v0.3.0.diff"'
check "手で反映するよう案内する" "必要な行を案件の Excel に手で反映してください" "$out"
ok "日本語の名前の型のファイルも取り込む" '[ "$(cat "$P/templates/不具合.md" 2>/dev/null)" = bug ]'
ok "案件と新しいタグの型の違いも出す" 'grep -q "^+| S-31 | テスト計画書 |" "$P/.tazuna-download/ID設計の型の差分-案件-v0.3.0.diff"' 
ok "取り出したものはコミットの対象にならない" '[ -z "$(g -C "$P" status --porcelain .tazuna-download)" ]'
ok "バージョンを記録する" '[ "$(cat "$P/harness/tazuna-version")" = v0.3.0 ]'

# 取り出すだけ
g -C "$P" commit -qam up3; rm -rf "$P/.tazuna-download"
out=$(cd "$P" && TAZUNA_REMOTE_URL="$T" bash scripts/tazuna-update.sh --id-design v0.3.0 2>&1)
ok "--id-design は Excel を取り出す" '[ -e "$P/.tazuna-download/ID設計-v0.3.0.xlsx" ]'
ok "--id-design は案件のファイルを変えない" '[ -z "$(g -C "$P" status --porcelain)" ]'

# 前のタグがない案件（手で取り込んできた）: 案件の書き出しと比べる
g -C "$P" add -A; g -C "$P" commit -qm up4 >/dev/null; echo v0.0.9 > "$P/harness/tazuna-version"; g -C "$P" commit -qam nover; rm -rf "$P/.tazuna-download"
printf '# ID 設計\n\n## 書類の種類\n\n| S-22 | 処理設計書 |\n| S-23 | ジョブ設計書 |\n' > "$T/docs/design/ID設計.md"
g -C "$T" commit -qam v4 && g -C "$T" tag v0.4.0
out=$(cd "$P" && TAZUNA_REMOTE_URL="$T" bash scripts/tazuna-update.sh v0.4.0 2>&1)
ok "前のタグがなければ、案件の型と比べて取り出す" '[ -e "$P/.tazuna-download/ID設計-v0.4.0.xlsx" ]'
ok "案件との差分に足りない行が出る" 'grep -q "^+| S-23 | ジョブ設計書 |" "$P/.tazuna-download/ID設計の型の差分-案件-v0.4.0.diff"'
ok "前のタグとの差分は作らない" '[ -z "$(ls "$P/.tazuna-download" | grep "v0.0.9")" ]'

echo "tazuna-update: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
