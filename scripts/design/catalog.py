"""ID 設計の原本（docs/design/ID設計.xlsx）と、その書き出し（docs/design/ID設計.md）を読み書きする。

原本は Excel。人は Excel だけを直す。
  機能一覧   … 人が書く。機能と、それを作る画面・ジョブ・IF・帳票・テーブル
  書類一覧   … id_design.py list が機能一覧から作る。人は「作成」（書く・書かない）と理由だけを付ける
  進捗・網羅状況 … id_design.py progress が作る
  書類の種類・記載項目・振り分け表 … 型。案件で育ててよい
書き出し（ID設計.md）は、PR で差分を読むためと、Lint・転記ツールが Excel なしで読むためのもの。
id_design.py export で作り、Lint（COMMON-009）が Excel と食い違っていないかを確かめる。

Excel を読む関数は openpyxl を使う（pip install openpyxl）。書き出しを読む関数は標準ライブラリだけで動く。
"""
import os
import re

XLSX = "ID設計.xlsx"
SNAPSHOT = "ID設計.md"
SPLIT = re.compile(r"\s*[、,]\s*")
LAYER = {"共通設計": "共通", "開発・運用": "共通", "機能別設計": "機能別"}

# 書き出しの表（セクション名, 列）。この順に書き、この列名で読む
TABLES = [
    ("機能一覧", ["機能", "画面", "ジョブ", "IF", "帳票", "テーブル", "説明"]),
    ("書類一覧", ["書類実体ID", "書類ID", "書類名", "名前", "機能", "作成", "理由"]),
    ("書類の種類", ["書類ID", "書類名", "区分", "作る単位", "目的", "主な読み手", "書く人", "承認する人"]),
    ("記載項目", ["書類ID", "項番", "設計項目", "記載", "この書類で書くこと"]),
    ("設計項目", ["項番", "観点", "設計項目", "性質", "機械検査", "業務承認", "記述の型", "決めること", "例", "型で用意済み"]),
]


def split(cell):
    return [s for s in SPLIT.split(cell or "") if s and s not in ("—", "-")]


# ---------------------------------------------------------------- Excel

def read_excel(path):
    """Excel から、書き出しと同じ形の辞書（セクション名 → 行の辞書のリスト）を作る"""
    from openpyxl import load_workbook
    wb = load_workbook(path)  # 数式は読まない（数式の列は使わない）

    def rows(sheet, cols):
        ws = wb[sheet]
        head = [c.value for c in ws[1]]
        idx = {name: head.index(name) for name in cols if name in head}
        out = []
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not any(v not in (None, "") for v in r):
                continue
            out.append({name: ("" if idx.get(name) is None or r[idx[name]] is None else str(r[idx[name]]).strip()) for name in cols})
        return out

    data = {}
    data["機能一覧"] = rows("機能一覧", TABLES[0][1])
    data["書類一覧"] = rows("書類一覧", TABLES[1][1])
    data["書類の種類"] = rows("書類の種類", TABLES[2][1])
    data["記載項目"] = [r for r in rows("記載項目", ["書類ID", "項番", "設計項目", "記載", "この書類で書くこと"]) if r["書類ID"]]
    data["設計項目"] = rows("振り分け表", TABLES[4][1])
    return data


# ---------------------------------------------------------------- 書き出し（md）

HEADER = """# ID 設計（書き出し）

> `docs/design/ID設計.xlsx` から `python3 scripts/design/id_design.py export` で作る書き出しです。**直接編集しないでください**。
> 原本は Excel です。PR ではこのファイルの差分で、機能一覧・書類一覧・型の変更をレビューします。
> Lint と転記ツールはこのファイルを読みます。Excel と食い違っていると Lint（COMMON-009）が止めます。
"""


def cell(v):
    return (v or "").replace("|", "｜").replace("\n", " ")


def render_snapshot(data):
    out = [HEADER]
    for name, cols in TABLES:
        out += [f"## {name}", "", "| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for r in data.get(name, []):
            out.append("| " + " | ".join(cell(r.get(c, "")) for c in cols) + " |")
        out.append("")
    return "\n".join(out)


def write_snapshot(data, path):
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(render_snapshot(data))


def read_snapshot(path):
    """書き出しを読む。ファイルがなければ None"""
    if not os.path.exists(path):
        return None
    data, current, cols = {}, None, None
    with open(path, encoding="utf-8") as fp:
        for raw in fp:
            line = raw.rstrip("\n")
            if line.startswith("## "):
                current, cols = line[3:].strip(), None
                data.setdefault(current, [])
            elif current and line.startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if cols is None:
                    cols = cells
                elif set(line.replace("|", "").strip()) <= {"-", " "}:
                    continue
                else:
                    cells += [""] * (len(cols) - len(cells))
                    data[current].append(dict(zip(cols, cells)))
    return data


# ---------------------------------------------------------------- 使いやすい形

class Catalog:
    """書き出し（または Excel）の中身を、Lint・転記ツールが使う形にしたもの"""

    def __init__(self, data):
        self.data = data
        self.items = {r["項番"]: r for r in data.get("設計項目", [])}
        self.docs = {r["書類ID"]: r for r in data.get("書類の種類", [])}
        self.records = {}
        for r in data.get("記載項目", []):
            self.records.setdefault(r["書類ID"], {})[r["項番"]] = r
        self.instances = {}
        self.duplicates = []
        for r in data.get("書類一覧", []):
            if r["書類実体ID"] in self.instances:
                self.duplicates.append(r["書類実体ID"])
            self.instances[r["書類実体ID"]] = dict(r, funcs=split(r.get("機能")))

    def layer(self, doc):
        return LAYER.get(self.docs.get(doc, {}).get("区分", ""), "共通")

    def function_of(self, inst):
        """書類実体が属する処理設計書（S-22-nnn）。処理設計書自身は自分、共通の書類は None"""
        r = self.instances.get(inst)
        if inst.startswith("S-22-"):
            return inst
        return r["funcs"][0] if r and r["funcs"] else None


def load(folder):
    """設計書のフォルダから書き出しを読む。なければ None"""
    data = read_snapshot(os.path.join(folder, SNAPSHOT))
    return Catalog(data) if data is not None else None


def destination(n, c, a):
    """振り分けルール（Excel の振り分け表の数式と同じ）。(主, 副)"""
    if n == "行為・操作":
        return "hooks", "AIへの条件"
    if n == "背景知識":
        return "知識", ""
    if c == "静的に可":
        return ("Lint" if n == "構造・依存" else "設計"), ("根拠" if a == "要" else "")
    if c == "実行で可":
        return ("実行検証" if n == "方針・判断" else "テスト"), ("根拠" if a == "要" else "")
    return ("人のための設計", "AIへの条件") if a == "要" else ("AIへの条件", "")


# ---------------------------------------------------------------- 設計書ファイル

FILE_RE = re.compile(r"^(S-(\d{2}))-(\d{3})_(.+)\.md$")
HEAD_RE = re.compile(r"^## (D-\d{5}) (.+?)\s*$")
LINE_RE = re.compile(r"^- \[(\d+)\] (.*)$")
# 他の行への参照: 同じ書類の中は「D-04001 の [1] → [3]」、別の書類は「S-22-001/D-04001/1」
REF_LOCAL_RE = re.compile(r"(D-\d{5})\s*の\s*((?:\[\d+\](?:\s*(?:→|、|,|・|と|から)\s*)?)+)")
REF_FULL_RE = re.compile(r"(S-\d{2}-\d{3})/(D-\d{5})/(\d+)")
NA_RE = re.compile(r"^該当なし")


def parse_design(text):
    """設計書の本文を読む。行は「- [番号] 本文」。番号は見出しの中で付ける。
    heads: [(行番号, 項番 or None, 見出しの名前)]
    lines: [(行番号, 番号 or None（形が違う行）, 本文, 直前の見出しの項番)]
    na: 「該当なし（理由）」と書いた見出しの項番の集合"""
    heads, lines, na, current = [], [], set(), None
    for n, raw in enumerate(text.splitlines(), 1):
        if raw.startswith("## "):
            m = HEAD_RE.match(raw)
            heads.append((n, m.group(1) if m else None, m.group(2) if m else raw[3:]))
            current = m.group(1) if m else "?"
        elif raw.startswith("- "):
            m = LINE_RE.match(raw)
            lines.append((n, m.group(1) if m else None, m.group(2) if m else raw[2:], current))
        elif current and NA_RE.match(raw.strip()):
            na.add(current)
    return heads, lines, na


def line_id(inst, item, num):
    """行のID。書類実体／見出しの項番／見出しの中の番号（例 S-23-001/D-08002/2）"""
    return f"{inst}/{item}/{num}"


def refs(text):
    """本文の中の参照。[(書類実体 or None（同じ書類）, 項番, 番号)]"""
    out = [(m.group(1), m.group(2), m.group(3)) for m in REF_FULL_RE.finditer(text)]
    for m in REF_LOCAL_RE.finditer(text):
        out += [(None, m.group(1), n) for n in re.findall(r"\[(\d+)\]", m.group(2))]
    return out


def design_files(folder):
    """{書類実体ID: ファイル名}"""
    out = {}
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        m = FILE_RE.match(name)
        if m:
            out[f"{m.group(1)}-{m.group(3)}"] = name
    return out


def file_name(inst, name):
    return f"{inst}_{re.sub(r'[\\\\/:*?\"<>|\\s]', '', name)}.md"
