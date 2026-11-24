"""設計書のレビュー（base-design-review）の材料を集める。読むだけで、何も書き換えない。

    python3 scripts/design/review_pack.py [--design docs/design] [--root .]

ルールで集められるものだけを集め、比べて判断するのはレビューする側（エージェントと人）に任せる。
  1. 同じ設計項目の行が2つ以上の書類にあるもの（食い違い・重複・置き場所を見る入口）
  2. 定義の一覧（ロール・区分値・メッセージ・用語・テーブルと列）。設計書で使っているのに定義がないものを見る
  3. 機能ごとの決定の行とテスト仕様の行。テスト仕様が触れていない決定を見る
"""
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog  # noqa: E402

# 定義を書く設計項目（ID設計.xlsx の設計項目の番号。番号は付け直さないので固定してよい）
DEFINES = {"D-11002": "ロール（機能の認可）", "D-05005": "区分値（コード値の定義）",
           "D-02007": "選択肢・コード値", "D-10001": "メッセージ"}


def read(path):
    with open(path, encoding="utf-8") as fp:
        return fp.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("TAZUNA_ROOT", "."))
    ap.add_argument("--design")
    a = ap.parse_args()
    design = a.design or os.path.join(a.root, "docs", "design")
    cat = catalog.load(design)
    if cat is None:
        sys.exit("ID設計.md がありません")
    files = catalog.design_files(design)
    lines = {}  # 書類実体ID → [(行ID, 項番, 本文, 添付)]
    for inst, name in sorted(files.items()):
        _, ls, _, attach, _ = catalog.scan_design(read(os.path.join(design, name)))
        lines[inst] = [(catalog.line_id(inst, u, n), u, t, attach.get(ln, "")) for ln, n, t, u in ls
                       if n and u and not t.startswith("（廃止）")]

    def kind(inst):
        f = cat.function_of(inst)
        return "共通" if not f else ("機能" if f == inst else f"機能（{f}）")

    out = ["# 設計書レビューの材料", "", f"書類 {len(files)} 件・行 {sum(len(v) for v in lines.values())} 行", ""]

    out += ["## 1. 同じ設計項目の行が2つ以上の書類にあるもの", "",
            "食い違い・同じ決まりの重複・共通に書くべき内容が機能の書類にないかを比べる。", ""]
    by_item = {}
    for inst, ls in lines.items():
        for lid, item, text, _ in ls:
            by_item.setdefault(item, []).append((inst, lid, text))
    for item in sorted(by_item):
        if len({i for i, _, _ in by_item[item]}) < 2:
            continue
        out.append(f"### {item} {cat.items.get(item, {}).get('設計項目', '')}")
        out += [f"- [{kind(i)}] {lid} {t}" for i, lid, t in by_item[item]]
        out.append("")

    out += ["## 2. 定義の一覧", "", "設計書で使っている名前・値がここにないものを見る。", ""]
    for item, label in DEFINES.items():
        rows = by_item.get(item, [])
        if rows:
            out.append(f"### {label}（{item}）")
            out += [f"- {lid} {t}" for _, lid, t in rows]
            out.append("")
    gl = os.path.join(a.root, "docs", "domain", "glossary.md")
    if os.path.isfile(gl):
        out += ["### 用語（docs/domain/glossary.md）"] + [l for l in read(gl).splitlines() if l.startswith("| ") and "---" not in l] + [""]
    sqls = sorted(glob.glob(os.path.join(a.root, "db", "schema", "*.sql")))
    if sqls:
        out.append("### テーブルと列（db/schema）")
        for p in sqls:
            text = read(p)
            for m in re.finditer(r"CREATE\s+TABLE\s+(\w+)\s*\((.*?)\n\);", text, re.S | re.I):
                cols = [c.split()[0] for c in (x.strip() for x in m.group(2).split("\n"))
                        if c and not re.match(r"(CONSTRAINT|PRIMARY|FOREIGN|UNIQUE|CHECK)\b", c, re.I)]
                checks = re.findall(r"CHECK\s*\((.*?)\)\s*,?\s*$", m.group(2), re.M | re.I)
                out.append(f"- {m.group(1)}: {', '.join(cols)}" + (f"（CHECK: {' / '.join(checks)}）" if checks else ""))
        out.append("")

    out += ["## 3. 機能ごとの決定とテスト仕様", "", "テスト仕様のどの行も触れていない決定、決定と食い違うテスト仕様を見る。", ""]
    centers = sorted({cat.function_of(i) for i in lines if cat.function_of(i)})
    for c in centers:
        members = sorted(i for i in lines if cat.function_of(i) == c)
        specs = [i for i in members if cat.role(i.rsplit("-", 1)[0]) == "テスト仕様"]
        out.append(f"### {c} {cat.instances.get(c, {}).get('名前', '')}")
        for i in members:
            tag = "テスト仕様" if i in specs else "決定"
            out += [f"- [{tag}] {lid} {t}" for lid, _, t, _ in lines[i]]
        if not specs:
            out.append("- （この機能のテスト仕様の書類がない）")
        out.append("")
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
