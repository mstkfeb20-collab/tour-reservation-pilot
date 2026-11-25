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

no() { if grep -qF -- "$2" <<<"$3"; then fail=$((fail + 1)); echo "NG: $1（「$2」がある）"; else pass=$((pass + 1)); fi; }

# 案内の順: ファイルのない書類（もとになる設計書）に書けとは言わない。先にひな形を作る
python3 "$SNAP" "$w/docs/design/ID設計.tmp" "S-20-001|データモデル設計書|"
python3 - "$w/docs/design/ID設計.md" "$w/docs/design/ID設計.tmp" "$ROOT" <<'PY'
import sys
sys.path.insert(0, sys.argv[3] + "/scripts/design"); import catalog
d = catalog.read_snapshot(sys.argv[1]); d["書類一覧"] += catalog.read_snapshot(sys.argv[2])["書類一覧"]
catalog.write_snapshot(d, sys.argv[1])
PY
rm "$w/docs/design/ID設計.tmp"
out=$(run --local)
check "もとになる設計書のファイルがなければ、ひな形を先に案内する" "**設計書のひな形を作る（2 件）**" "$out"
no "ファイルのない設計書のテーブル一覧は案内しない" "テーブル一覧」を書く" "$out"

# 立ち上げ: テンプレートのままのファイルがあれば、最初に案内する
printf '# [プロジェクト名]\n' > "$w/AGENTS.md"
out=$(run --local)
check "AGENTS.md が見本のままなら立ち上げ" "## 今の段階: 立ち上げ" "$out"
check "AGENTS.md を書き換える案内" "**AGENTS.md をこの案件のものにする**（案件リーダー）" "$out"
rm "$w/AGENTS.md"; mkdir -p "$w/_tazuna"
no "origin のない _tazuna は tazuna 本体として扱う" "_tazuna/ を消す" "$(run --local)"
git -C "$w" init -q && git -C "$w" remote add origin https://example.com/org/my-project.git
check "案件のリポジトリに _tazuna が残っていれば消す" "**tazuna 本体専用のフォルダ _tazuna/ を消す**" "$(run --local)"
rm -rf "$w/_tazuna" "$w/.git"

# PR の質問: 人のコメントの「回答: n」「保留: n」で答えたものとする（本文は人が編集しない）
out=$(cd "$ROOT/scripts/report" && python3 -c '
import next as n
b = "## レビュアーに判断してほしいこと\n- 取消料は税込か\n- 返金の日付\n1. 窓口からの取消\n- 端数（保留）\n\n## ハーネスへのフィードバック\n- なし"
print(n.open_questions(b, ["回答: 1, 3"]))
print(n.open_questions(b, ["回答：１", "> 保留: 2", "回答: 3"]))')
check "コメントで答えていない質問が残る" "[(2, '返金の日付')]" "$out"
check "全角の番号・保留も答えとして扱う" "[]" "$out"

# 不具合の issue: 原因区分で行き先を変える
out=$(cd "$ROOT/scripts/report" && python3 -c '
import next as n
i = {"title": "【不具合】取消料がずれる", "labels": [{"name": "不具合"}]}
print(n.is_bug(i), n.is_bug({"title": "x", "labels": ["不具合"]}), n.is_bug({"title": "REQ-1"}))
for b in ["原因区分: （設計・転記・実装・ハーネスのどれか。分からなければ空）", "原因区分: 設計", "原因区分: 実装"]:
    print([t.what for t in n.bug_todos(i, 7, b, False, "割り当てる")])
print(n.bug_todos(i, 7, "原因区分: 実装", True, "割り当てる"))')
check "不具合を見分ける" "True True False" "$out"
check "原因が決まっていなければ切り分ける" "不具合 #7 の原因を切り分ける" "$out"
check "設計の誤りは設計書を直す" "不具合 #7 の設計書を直す" "$out"
check "実装の誤りは割り当てる" "不具合 #7 の修正を割り当てる" "$out"
check "割り当て済みの実装の誤りは何も出さない" "[]" "$out"

# 単体テストまで終わったら、結合テストへの引き渡しを出す
w2=$(mktemp -d); trap 'rm -rf "$w" "$w2"' EXIT
mkdir -p "$w2/docs/design" "$w2/docs/requirements" "$w2/src/test"
python3 "$SNAP" "$w2/docs/design/ID設計.md"
python3 - "$w2/docs/design" "$ROOT" <<'PY'
import os, sys
sys.path.insert(0, sys.argv[2] + "/scripts/design"); import catalog, id_design
p = os.path.join(sys.argv[1], "ID設計.md")
d = catalog.read_snapshot(p)
d["機能一覧"] = [{"機能": "予約取消", "画面": "", "ジョブ": "", "IF": "", "帳票": "", "説明": ""}]
names = {t["書類ID"]: t["書類名"] for t in d["書類の種類"]}
d["書類一覧"] = [{"書類実体ID": f"{doc}-{k:03d}", "書類ID": doc, "書類名": names[doc], "名前": name, "機能": "",
                 "作成": "書かない", "理由": "テスト"}
                for k, (doc, name, _) in enumerate(id_design.derive(d, sys.argv[1]), 1)]
catalog.write_snapshot(d, p)
PY
printf '## REQ-22001 予約取消\n\n- 完了条件:\n  - 取り消せる\n\n## テスト仕様\n\n- 前日は取り消せる（S-26-001/D-15001/1・正常系）\n- 手配会社の検証環境で通しで確かめる（S-26-001/D-15008/1・結合・総合テストの観点）\n' \
  > "$w2/docs/requirements/S-22-001_予約取消.md"
printf '@Tag("REQ-22001")\n@Tag("S-26-001/D-15001/1")\n' > "$w2/src/test/ATest.java"
out=$(TAZUNA_ROOT="$w2" python3 "$PY" --local 2>&1)
check "全要件にテストがあれば、単体テストまで完了" "## 今の段階: 単体テストまで完了（結合テストへ引き渡す）" "$out"
check "単体で確かめていない行を引き渡す" "S-26-001/D-15008/1 手配会社の検証環境で通しで確かめる" "$out"
check "確かめた行を数える" "テスト仕様 2 行のうち、単体テストで確かめた 1 行" "$out"

echo "next: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
