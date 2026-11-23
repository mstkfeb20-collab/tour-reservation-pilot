"""DDL（db/schema/*.sql）が説明を持っているかを確かめる（COMMON-010）。

DDL がテーブル・列の正。テーブル設計書（S-16）には DDL に書けない決定だけを書く。そのため DDL に次を求める。
  - すべてのテーブルと列に説明（COMMENT ON TABLE / COMMENT ON COLUMN、または列定義の COMMENT '...'）がある
  - 区分値の列（CHECK (列 IN (...))）の説明は、値の意味を決めた設計書の行（例 S-15-001/D-05005/2）を指す
    指した行が設計書にない場合はエラー（設計書のファイル自体がまだない場合は警告）
  - 値の範囲は CHECK 制約で書く（説明の文章だけで範囲を書かない）
書類一覧のテーブル設計書（S-16）と DDL のテーブルが対応しているかは警告で知らせる。

    python3 ddl_comments.py <リポジトリのルート>
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "design"))
import catalog  # noqa: E402

RULE = "COMMON-010"
REF = "docs/requirements/README.md（DDL が正）・ID設計.xlsx の S-16・S-20"
errors = 0

CREATE_RE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.\"]+)\s*\(", re.I)
CMT_TABLE_RE = re.compile(r"COMMENT\s+ON\s+TABLE\s+([\w.\"]+)\s+IS\s+'((?:[^']|'')*)'", re.I)
CMT_COL_RE = re.compile(r"COMMENT\s+ON\s+COLUMN\s+([\w.\"]+)\.([\w\"]+)\s+IS\s+'((?:[^']|'')*)'", re.I)
INLINE_RE = re.compile(r"\bCOMMENT\s*=?\s*'((?:[^']|'')*)'", re.I)
CHECK_IN_RE = re.compile(r"CHECK\s*\(\s*([\w\"]+)\s+IN\s*\(", re.I)
CONSTRAINT_HEAD = re.compile(r"^(CONSTRAINT|PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK|INDEX|KEY)\b", re.I)
LINE_ID_RE = re.compile(r"(S-\d{2}-\d{3})/(D-\d{5})/(\d+)")


def norm(name):
    return name.replace('"', "").split(".")[-1].upper()


def error(where, what, why, fix):
    global errors
    errors += 1
    print(f"ERROR [{RULE}] {where}\n  内容: {what}\n  理由: {why}\n  修正: {fix}\n  参照: {REF}", file=sys.stderr)


def warn(where, what):
    print(f"WARN  [{RULE}] {where} : {what}", file=sys.stderr)


def strip_comments(sql):
    sql = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), sql, flags=re.S)
    return re.sub(r"--[^\n]*", "", sql)


def split_top(body):
    """括弧の外のカンマで分ける"""
    out, depth, cur, quote = [], 0, "", False
    for ch in body:
        if ch == "'":
            quote = not quote
        elif not quote and ch == "(":
            depth += 1
        elif not quote and ch == ")":
            depth -= 1
        if ch == "," and depth == 0 and not quote:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [s.strip() for s in out if s.strip()]


def parse(sql):
    """{テーブル: {"line": 行番号, "comment": str|None, "cols": {列: {"comment", "code"}}}}"""
    tables = {}
    for m in CREATE_RE.finditer(sql):
        start, depth, i = m.end(), 1, m.end()
        while i < len(sql) and depth:
            depth += {"(": 1, ")": -1}.get(sql[i], 0)
            i += 1
        body, rest = sql[start:i - 1], sql[i:sql.find(";", i) if ";" in sql[i:] else len(sql)]
        t = {"line": sql[:m.start()].count("\n") + 1, "comment": None, "cols": {}}
        tm = INLINE_RE.search(rest)
        if tm:
            t["comment"] = tm.group(1)
        codes = set()
        for part in split_top(body):
            for c in CHECK_IN_RE.finditer(part):
                codes.add(norm(c.group(1)))
            if CONSTRAINT_HEAD.match(part):
                continue
            col = norm(part.split()[0])
            cm = INLINE_RE.search(part)
            t["cols"][col] = {"comment": cm.group(1) if cm else None}
        for c in codes:
            if c in t["cols"]:
                t["cols"][c]["code"] = True
        tables[norm(m.group(1))] = t
    for m in CMT_TABLE_RE.finditer(sql):
        if norm(m.group(1)) in tables:
            tables[norm(m.group(1))]["comment"] = m.group(2)
    for m in CMT_COL_RE.finditer(sql):
        t = tables.get(norm(m.group(1)))
        if t and norm(m.group(2)) in t["cols"]:
            t["cols"][norm(m.group(2))]["comment"] = m.group(3)
    return tables


def design_lines(design):
    """{書類実体ID: 行IDの集合}（設計書のファイルがあるものだけ）"""
    out = {}
    for inst, name in catalog.design_files(design).items():
        with open(os.path.join(design, name), encoding="utf-8") as fp:
            _, lines, _ = catalog.parse_design(fp.read())
        out[inst] = {catalog.line_id(inst, under, num) for _, num, text, under in lines
                     if num and under and not text.startswith("（廃止）")}
    return out


def main(root):
    schema = os.path.join(root, "db", "schema")
    if not os.path.isdir(schema):
        return 0
    design = os.path.join(root, "docs", "design")
    known = design_lines(design) if os.path.isdir(design) else {}
    all_tables = {}
    for name in sorted(os.listdir(schema)):
        if not name.lower().endswith(".sql"):
            continue
        rel = f"db/schema/{name}"
        with open(os.path.join(schema, name), encoding="utf-8") as fp:
            sql = strip_comments(fp.read())
        for tname, t in parse(sql).items():
            where = f"{rel}:{t['line']}"
            all_tables[tname] = where
            if not (t["comment"] or "").strip():
                error(where, f"テーブル {tname} に説明（COMMENT）がありません",
                      "DDL がテーブルの正です。説明がないと、何のテーブルかを設計書に探しに行くことになります",
                      f"COMMENT ON TABLE {tname} IS '何を持つテーブルか'; を足してください")
            for col, c in t["cols"].items():
                text = (c["comment"] or "").strip()
                if not text:
                    error(where, f"列 {tname}.{col} に説明（COMMENT）がありません",
                          "列の意味を DDL だけで分かるようにするためです（エージェントも協力会社も DDL を見て実装します）",
                          f"COMMENT ON COLUMN {tname}.{col} IS '列の意味'; を足してください。範囲は CHECK 制約で書きます")
                    continue
                if c.get("code"):
                    ref = LINE_ID_RE.search(text)
                    if not ref:
                        error(where, f"区分値の列 {tname}.{col} の説明が、値の意味を決めた設計書の行を指していません",
                              "区分値の意味はコード定義書で決めます。DDL と設計書で意味が二重に書かれると食い違います",
                              f"説明に値の意味を決めた行の ID を書いてください（例 '振込状況。値の意味は S-15-001/D-05005/2'）")
                    elif ref.group(1) not in known:
                        warn(where, f"{tname}.{col} が指す {ref.group(1)} の設計書がまだありません")
                    elif ref.group(0) not in known[ref.group(1)]:
                        error(where, f"{tname}.{col} が指す {ref.group(0)} が設計書にありません（廃止の行も指せません）",
                              "指した先がないと、値の意味を辿れません",
                              "設計書の行の ID に直すか、設計書に行を足してください")
    cat = catalog.load(design) if os.path.isdir(design) else None
    if cat and cat.instances:  # 書類一覧をまだ作っていない間は突き合わせない
        named = {}
        for inst, r in cat.instances.items():
            if cat.docs.get(r["書類ID"], {}).get("作る単位", "").startswith("テーブル") and r["作成"] == "書く":
                named[r["名前"].upper()] = inst
        for name, inst in sorted(named.items()):
            if name not in all_tables:
                warn("db/schema", f"書類一覧の {inst}（{name}）の CREATE TABLE がまだありません")
        for name, where in sorted(all_tables.items()):
            if name not in named:
                warn(where, f"テーブル {name} が書類一覧（機能一覧のテーブル）にありません")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TAZUNA_ROOT", ".")))
