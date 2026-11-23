#!/usr/bin/env python3
"""Word（.docx）・Excel（.xlsx）の設計書から、位置付きでテキストを取り出す。

    python3 .github/skills/base-spec-extraction/read_office.py <ファイルまたはフォルダ> ...

出力の各行の先頭に位置（出典）を付ける。
    [基本設計書.docx §2.処理手順 ¶5] ② ツアーの出発日を…
    [設計書.xlsx 改訂履歴!C3] 支払期限を出発日の7日前から10日前に変更
    [設計書.docx 表1 行2] J010_EXPORT | export_reserve.sh | reserve_export.csv

標準ライブラリだけで動く（python-docx・openpyxl は不要）。.md・.txt はそのまま行番号付きで出す。
"""
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _text(el, tag):
    return "".join(t.text or "" for t in el.iter(tag))


def read_docx(path: Path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(f"{W}body")
    section, para_no, table_no = "", 0, 0
    for el in body:
        if el.tag == f"{W}p":
            text = _text(el, f"{W}t").strip()
            if not text:
                continue
            style = el.find(f"{W}pPr/{W}pStyle")
            sval = style.get(f"{W}val", "") if style is not None else ""
            if re.match(r"(Heading|見出し|Title|表題)", sval) or re.fullmatch(r"\d+", sval or "x"):
                section, para_no = text, 0
                yield f"[{path.name} 見出し] {text}"
                continue
            para_no += 1
            where = f"§{section} " if section else ""
            yield f"[{path.name} {where}¶{para_no}] {text}"
        elif el.tag == f"{W}tbl":
            table_no += 1
            for row_no, tr in enumerate(el.iter(f"{W}tr"), 1):
                cells = [_text(tc, f"{W}t").strip() for tc in tr.iter(f"{W}tc")]
                if any(cells):
                    yield f"[{path.name} 表{table_no} 行{row_no}] " + " | ".join(cells)


def read_xlsx(path: Path):
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{S}si"):
                shared.append(_text(si, f"{S}t"))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = {r.get("Id"): r.get("Target") for r in rels.iter(f"{PR}Relationship")}
        for sheet in wb.iter(f"{S}sheet"):
            name = sheet.get("name")
            t = target.get(sheet.get(f"{R}id"), "")
            t = t.lstrip("/")
            part = t if t.startswith("xl/") else f"xl/{t}"
            if part not in names:
                continue
            ws = ET.fromstring(z.read(part))
            for row in ws.iter(f"{S}row"):
                values = []
                for c in row.iter(f"{S}c"):
                    kind, ref = c.get("t"), c.get("r")
                    if kind == "s":
                        v = c.find(f"{S}v")
                        val = shared[int(v.text)] if v is not None else ""
                    elif kind == "inlineStr":
                        val = _text(c, f"{S}t")
                    else:
                        v = c.find(f"{S}v")
                        val = v.text if v is not None else ""
                    if val not in ("", None):
                        values.append((ref, val))
                if values:
                    first = values[0][0]
                    yield f"[{path.name} {name}!{first}] " + " | ".join(v for _, v in values)


def read_plain(path: Path):
    for no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.strip():
            yield f"[{path.name} L{no}] {line}"


READERS = {".docx": read_docx, ".xlsx": read_xlsx, ".xlsm": read_xlsx, ".md": read_plain, ".txt": read_plain}


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    files = []
    for a in argv:
        p = Path(a)
        files += sorted(f for f in p.rglob("*") if f.suffix.lower() in READERS) if p.is_dir() else [p]
    for f in files:
        reader = READERS.get(f.suffix.lower())
        if reader is None:
            print(f"[{f.name}] 読めない形式です（.doc・.xls は .docx・.xlsx に変換してください）", file=sys.stderr)
            continue
        print(f"===== {f} =====")
        try:
            for line in reader(f):
                print(line)
        except (zipfile.BadZipFile, KeyError, ET.ParseError) as e:
            print(f"[{f.name}] 読み取りに失敗しました: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
