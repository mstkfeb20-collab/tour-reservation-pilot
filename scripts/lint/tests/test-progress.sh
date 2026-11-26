#!/usr/bin/env bash
# id_design.py progress の自己テスト。複数人の進み具合を、統合先のブランチと開いている PR から決めるか。
# GitHub は、決まった答えを返す gh のまねで代える。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; PY="$ROOT/scripts/design/id_design.py"; pass=0; fail=0
python3 -c 'import openpyxl' 2>/dev/null || { echo "openpyxl がないので飛ばします（pip install openpyxl）"; exit 0; }
check() { if grep -qF -- "$2" <<<"$3"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: $1（「$2」がない）"; echo "$3" | sed 's/^/    /'; fi; }
ok() { if eval "$2"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: $1"; fi; }
g() { git -C "$w" -c user.name=t -c user.email=t@example.com "$@"; }

w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
mkdir -p "$w/docs/design" "$w/bin"
cp "$ROOT/docs/design/ID設計.xlsx" "$w/docs/design/"
python3 - "$w/docs/design/ID設計.xlsx" <<'PY'
import sys
from openpyxl import load_workbook
wb = load_workbook(sys.argv[1])
for s in [n for n in ("機能一覧", "書類一覧", "進捗", "網羅状況") if n in wb.sheetnames]:
    ws = wb[s]
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)
wb["機能一覧"].append(["予約取消", "", "", "", "", ""])
wb.save(sys.argv[1])
PY
run() { (cd "$w" && TAZUNA_ROOT="$w" TAZUNA_PLATFORM=github PATH="$w/bin:$PATH" python3 "$PY" "$@" 2>&1); }
g init -q -b main
run list >/dev/null; run scaffold >/dev/null
g add -A && g commit -qm 設計の準備

# 書類を4つ選ぶ: 統合済み・ドラフトの PR・レビュー中の PR・手元だけ
mapfile -t docs < <(cd "$w/docs/design" && ls S-*.md | head -4)
[ "${#docs[@]}" -eq 4 ] || { echo "NG: 設計書のひな形が4つ以上できていない"; exit 1; }
id() { grep -oE '^S-[0-9]{2}-[0-9]{3}' <<<"$1"; }
write() { python3 - "$w/docs/design/$1" <<'PY'
import sys, re
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
m = re.search(r"^## .*$", t, re.M)
open(p, "w", encoding="utf-8").write(t[:m.end()] + "\n\n- [1] 書いた決定" + t[m.end():])
PY
}
write "${docs[0]}"; g commit -qam 統合済み
write "${docs[3]}"   # 手元だけ（コミットも PR もしていない）

# gh のまね: #1 はドラフト（docs[1] を書いている）、#2 はレビュー中（docs[2]）
cat > "$w/bin/gh" <<EOF
#!/usr/bin/env bash
case "\$*" in
  *"pulls?state=open"*) echo '[{"number":1,"draft":true,"user":{"login":"tanaka"}},{"number":2,"draft":false,"user":{"login":"sato"}}]' ;;
  *"pulls/1/files"*) echo '[{"filename":"docs/design/${docs[1]}"}]' ;;
  *"pulls/2/files"*) echo '[{"filename":"docs/design/${docs[2]}"},{"filename":"src/A.java"}]' ;;
  *) exit 1 ;;
esac
EOF
chmod +x "$w/bin/gh"

before=$(sha1sum "$w/docs/design/ID設計.xlsx")
out=$(run progress --base main)
check "ドラフトの PR が触る設計書は執筆中" "執筆中: $(id "${docs[1]}")" "$out"
check "執筆中は誰の PR かを出す" "#1 tanaka（ドラフト）" "$out"
check "ドラフトでない PR が触る設計書はレビュー中" "レビュー中: $(id "${docs[2]}")" "$out"
check "手元だけの変更は、PR がないと分かるように出す" "手元で変更中（PR なし）: $(id "${docs[3]}")" "$out"
check "一覧はコミットしないフォルダに出す" ".tazuna-local/進捗.xlsx" "$out"
ok "一覧のファイルができる" '[ -f "$w/.tazuna-local/進捗.xlsx" ]'
ok "ID設計.xlsx は変えない" '[ "$(sha1sum "$w/docs/design/ID設計.xlsx")" = "$before" ]'
ok "一覧はコミットの対象にならない" '[ -z "$(g status --porcelain .tazuna-local)" ]'
state=$(python3 - "$w/.tazuna-local/進捗.xlsx" "$(id "${docs[0]}")" <<'PY'
import sys
from openpyxl import load_workbook
ws = load_workbook(sys.argv[1])["進捗"]
head = [c.value for c in ws[1]]
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[0] == sys.argv[2]: print(r[head.index("状態")])
PY
)
ok "統合先に入った設計書は、統合先の内容で決める（必須不足か完了）" '[ "$state" = 必須不足 ] || [ "$state" = 完了 ]'

# 手元が統合先より遅れていても（まだ pull していない）、自分の変更とは扱わない
g checkout -q -- "docs/design/${docs[3]}"
g checkout -q -b old HEAD~1
out=$(run progress --base main)
ok "遅れているだけなら手元の変更と扱わない" '! grep -qF "手元で変更中（PR なし）: $(id "${docs[0]}")" <<<"$out"'

# PR を読めないときは、そう伝えて統合先だけで決める
rm "$w/bin/gh"; printf '#!/bin/sh\nexit 1\n' > "$w/bin/gh"; chmod +x "$w/bin/gh"
out=$(run progress --base main)
check "PR を読めないと伝える" "開いている PR は読めませんでした" "$out"

echo "progress: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
