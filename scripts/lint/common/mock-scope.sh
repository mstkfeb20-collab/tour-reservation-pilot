#!/usr/bin/env bash
# モックにしてよいのはポート（interface）だけ（COMMON-012）。
# 業務ロジックのクラス（class・record・enum）をモックや spy にすると、確かめたいものを置き換えたまま通るテストになる。
# 見るのは src/test の mock(X.class)・@Mock X・spy(...)・@Spy。X の定義は src/main から探す（見つからない型＝外部ライブラリは見ない）。
source "$(dirname "$0")/../lib.sh"

[ -d "$TAZUNA_ROOT/src/test" ] || lint_finish
out=$(python3 - "$TAZUNA_ROOT" <<'PY'
import os, re, sys
root = sys.argv[1]
kinds = {}
for d, _, fs in os.walk(os.path.join(root, "src", "main")):
    for f in fs:
        if f.endswith(".java"):
            text = open(os.path.join(d, f), encoding="utf-8").read()
            m = re.search(r"\b(class|interface|record|enum)\s+" + re.escape(f[:-5]) + r"\b", text)
            if m:
                kinds[f[:-5]] = m.group(1)
pats = [re.compile(r"\bmock\(\s*(\w+)\.class"), re.compile(r"@Mock\b[^;=]*?\b(\w+)\s+\w+\s*[;=]")]
spy = [re.compile(r"\bspy\("), re.compile(r"@Spy\b")]
for d, _, fs in os.walk(os.path.join(root, "src", "test")):
    for f in fs:
        if not f.endswith(".java"):
            continue
        path = os.path.join(d, f)
        for n, line in enumerate(open(path, encoding="utf-8"), 1):
            rel = os.path.relpath(path, root)
            for p in pats:
                for t in p.findall(line):
                    if kinds.get(t) in ("class", "record", "enum"):
                        print(f"{rel}:{n}\t{t} は {kinds[t]} です（モックにしてよいのは interface だけ）")
            if any(p.search(line) for p in spy):
                print(f"{rel}:{n}\tspy は実物の一部だけを置き換えるので使わない")
PY
)
while IFS=$'\t' read -r where what; do
  [ -n "$where" ] || continue
  lint_error "COMMON-012" "$where" "$what" \
    "業務ロジックをモックにすると、確かめたいものを置き換えたまま通るテストになります" \
    "実物のクラスを使ってください。DB や外部との境界なら、domain に interface（ポート）を置き、それをモックにしてください" \
    ".github/skills/base-test-design/SKILL.md"
done <<< "$out"
lint_finish
