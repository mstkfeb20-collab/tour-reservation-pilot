#!/usr/bin/env bash
# scripts/report/next.py（案内役）の自己テスト。GitHub は見ない（--local）。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; PY="$ROOT/scripts/report/next.py"; SNAP="$ROOT/scripts/lint/tests/snapshot-for-test.py"; pass=0; fail=0
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
check() { if grep -qF -- "$2" <<<"$3"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: $1（「$2」がない）"; echo "$3" | sed 's/^/    /'; fi; }
run() { TAZUNA_ROOT="$w" python3 "$PY" "$@" 2>&1; }
mkdir -p "$w/docs/design" "$w/docs/requirements" "$w/src/test"

python3 "$SNAP" "$w/docs/design/ID設計.md"
# 案件のリポジトリでは機能一覧が書いてあるので、空にしてから始める
python3 - "$w/docs/design/ID設計.md" "$ROOT" <<'EOF2'
import sys
sys.path.insert(0, sys.argv[2] + "/scripts/design"); import catalog
d = catalog.read_snapshot(sys.argv[1]); d["機能一覧"] = []; catalog.write_snapshot(d, sys.argv[1])
EOF2
check "機能一覧が空なら、分かっている範囲で書くよう案内する" "**機能一覧を、分かっている範囲で書く**（社員）" "$(run --local)"

python3 - "$w/docs/design/ID設計.md" "$ROOT" <<'EOF'
import sys
sys.path.insert(0, sys.argv[2] + "/scripts/design"); import catalog
d = catalog.read_snapshot(sys.argv[1])
d["機能一覧"] = [{"機能": "予約取消", "画面": "予約取消画面", "ジョブ": "", "IF": "", "帳票": "", "説明": ""}]
catalog.write_snapshot(d, sys.argv[1])
EOF
out=$(run --local)
check "機能一覧と書類一覧がずれていれば、書類一覧を作り直す" "**書類一覧を作り直す**（社員）" "$out"
check "書類一覧がまだなければ段階は準備" "## 今の段階: 準備" "$out"

python3 "$SNAP" "$w/docs/design/ID設計.tmp" "S-22-001|予約取消|"
python3 - "$w/docs/design/ID設計.md" "$w/docs/design/ID設計.tmp" "$ROOT" <<'EOF'
import sys
sys.path.insert(0, sys.argv[3] + "/scripts/design"); import catalog
d = catalog.read_snapshot(sys.argv[1]); d["書類一覧"] = catalog.read_snapshot(sys.argv[2])["書類一覧"]
catalog.write_snapshot(d, sys.argv[1])
EOF
rm "$w/docs/design/ID設計.tmp"
out=$(run --local)
check "ファイルのない書類は、ひな形を作る" "**設計書のひな形を作る（1 件）**" "$out"

printf '## REQ-22001 予約取消\n\n- 完了条件:\n  - 取り消せる\n' > "$w/docs/requirements/S-22-001_予約取消.md"
out=$(run --local)
check "テストのない要件は、issue を作る" "**REQ-22001 を実装する issue を作る**" "$out"
out=$(run --issue REQ-22001)
check "issue の下書きに対象要件の行" "対象要件: REQ-22001" "$out"
check "issue の下書きに要件のファイル" '`docs/requirements/S-22-001_予約取消.md`（完了条件' "$out"
check "ない要件の下書き" "REQ-99999 は docs/requirements/ にありません" "$(run --issue REQ-99999)"
echo '@Tag("REQ-22001")' > "$w/src/test/ATest.java"
out=$(run --local)
[ -z "$(grep -F 'REQ-22001 を実装する issue' <<<"$out")" ] && pass=$((pass + 1)) || { fail=$((fail + 1)); echo "NG: テストのある要件は issue を求めない"; }

echo "next: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
