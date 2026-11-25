"""設計書の「書かれていないこと」のうち、機械で分かるものを集める。Lint・案内役・レポート・レビューの材料が使う。

stars:   ★ 共通の書類の必須の見出しが空なのに、機能の書類が同じ設計項目を決めている
missing_refs: 設計書の行が指すファイルが実在しない（転記で作られる要件・作業一覧のファイルと、書類一覧のテーブルの DDL は、まだなくてもよい）
tables:  S-20 データモデル設計書の「テーブル一覧」（D-05020）の行の先頭の名前（テーブル設計書はここから作る）
crud:    処理設計書の CRUD（D-05006）の行に出てくる名前を、テーブル一覧・DDL（db/schema）と突き合わせる。
         テーブルごとに、どの行が触るか（逆引き）と、テーブルにも列にもない名前を返す
table_vs_ddl: テーブル一覧にあるのに DDL がないもの、DDL があるのにテーブル一覧にないもの
"""
import glob
import os
import re

import catalog

PATH_RE = re.compile(r"(?<![\w/.-])((?:docs|db|src|scripts|\.github)/[\w./\-ぁ-んァ-ヶ一-龠ー・（）]+?\.(?:md|sql|java|py|sh|yml|yaml|xlsx|json|txt|csv))")


def _read(path):
    with open(path, encoding="utf-8") as fp:
        return fp.read()


def written(folder, cat=None):
    """{書類実体ID: ({書いた設計項目}, {該当なしの設計項目}, [(行ID, 項番, 本文)])}"""
    cat = cat or catalog.load(folder)
    out = {}
    for inst, name in catalog.design_files(folder).items():
        _, lines, na = catalog.parse_design(_read(os.path.join(folder, name)))
        live = [(catalog.line_id(inst, u, n), u, t) for _, n, t, u in lines if n and u and not t.startswith("（廃止）")]
        out[inst] = ({u for _, u, _ in live}, set(na), live)
    return out


def stars(folder, cat=None, w=None):
    """[(共通の書類実体ID, 設計項目, 設計項目名, [(機能の書類実体ID, 行ID)])]"""
    cat = cat or catalog.load(folder)
    w = w or written(folder, cat)
    used = {}
    for inst, (_, _, live) in w.items():
        if cat.function_of(inst):
            for lid, item, _ in live:
                used.setdefault(item, []).append((inst, lid))
    out = []
    for inst, (items, na, _) in sorted(w.items()):
        if cat.function_of(inst) or inst not in cat.instances:
            continue
        doc = cat.instances[inst]["書類ID"]
        for item, rec in cat.records.get(doc, {}).items():
            if rec["記載"] == "必須" and item not in items and item not in na and item in used:
                out.append((inst, item, cat.items.get(item, {}).get("設計項目", ""), used[item]))
    return out


def missing_refs(root, folder, cat=None, w=None):
    """[(行ID, パス, 'error' か 'warn')]。docs/ と db/ の参照先がなければ error、それ以外（src/ など、まだ作っていないコード）は warn"""
    cat = cat or catalog.load(folder)
    w = w or written(folder, cat)
    allowed = set()
    try:
        import transcribe
        want, headers, _ = transcribe.plan(folder)
        allowed |= set(want) | set(headers)
    except Exception:  # 転記の計画が作れなくても参照の検査は続ける
        pass
    for r in cat.instances.values():
        if cat.docs.get(r["書類ID"], {}).get("作る単位", "").startswith("テーブル") and r["作成"] == "書く":
            allowed.add(f"db/schema/{r['名前']}.sql")
    out = []
    for inst, (_, _, live) in sorted(w.items()):
        for lid, _, text in live:
            for p in PATH_RE.findall(text):
                if os.path.exists(os.path.join(root, p)) or p in allowed:
                    continue
                out.append((lid, p, "error" if p.startswith(("docs/", "db/")) else "warn"))
    return out


CRUD_ITEM = "D-05006"
TABLE_DOC, TABLE_ITEM = "S-20", "D-05020"
NAME_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Z][A-Z0-9_]{2,}(?![A-Za-z0-9_])")
NOT_TABLE = {"INSERT", "UPDATE", "DELETE", "SELECT", "MERGE", "UPSERT", "CRUD", "NULL", "AND", "NOT", "SQL", "DDL",
             "CSV", "API", "JOIN", "WHERE", "COMMIT", "ROLLBACK", "LOCK", "TRUNCATE"}


def ddl(root):
    """{テーブル名: {列名}}。db/schema/*.sql の CREATE TABLE から読む（ファイル名もテーブル名として扱う）"""
    out = {}
    for p in sorted(glob.glob(os.path.join(root, "db", "schema", "*.sql"))):
        out.setdefault(os.path.splitext(os.path.basename(p))[0].upper(), set())
        for m in re.finditer(r"CREATE\s+TABLE\s+(?:\w+\.)?\"?(\w+)\"?\s*\((.*?)\n\s*\)\s*;", _read(p), re.S | re.I):
            cols = {c.upper() for c in re.findall(r"^\s*\"?(\w+)\"?\s+\w", m.group(2), re.M)}
            out.setdefault(m.group(1).upper(), set()).update(cols - {"CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK"})
    return out


def tables(folder, w=None):
    """{テーブル名: 行ID}（S-20 のテーブル一覧の行の先頭の名前。大文字にそろえる）"""
    w = w or written(folder)
    out = {}
    for inst, (_, _, live) in sorted(w.items()):
        if inst.startswith(TABLE_DOC + "-"):
            for lid, item, text in live:
                m = re.match(r"\s*([A-Za-z][A-Za-z0-9_]*)", text)
                if item == TABLE_ITEM and m:
                    out.setdefault(m.group(1).upper(), lid)
    return out


def table_vs_ddl(root, folder, w=None):
    """([(行ID, テーブル一覧にあるのに DDL がない名前)], [DDL があるのにテーブル一覧にない名前])。テーブル一覧がまだなければ ([], [])"""
    listed = tables(folder, w)
    if not listed:
        return [], []
    have = ddl(root)
    return ([(lid, n) for n, lid in listed.items() if n not in have],
            sorted(n for n in have if n not in listed))


def crud(root, folder, cat=None, w=None):
    """({テーブル名: [行ID]}, [(行ID, テーブル一覧にも DDL にもない名前)])。CRUD の行の大文字の名前を、テーブル一覧・DDL のテーブルと列に突き合わせる"""
    cat = cat or catalog.load(folder)
    w = w or written(folder, cat)
    have = ddl(root)
    known = set(have) | set(tables(folder, w))
    cols = set().union(*have.values()) if have else set()
    uses, unknown = {}, []
    for inst, (_, _, live) in sorted(w.items()):
        for lid, item, text in live:
            if item != CRUD_ITEM:
                continue
            for name in dict.fromkeys(NAME_RE.findall(text)):
                if name in known:
                    uses.setdefault(name, []).append(lid)
                elif name in cols or name in NOT_TABLE or re.fullmatch(r"[A-Z]{1,2}\d+[A-Z]?", name):
                    continue  # 列名・SQL の言葉・ジョブ ID（J110 など）
                else:
                    unknown.append((lid, name))
    return uses, unknown
