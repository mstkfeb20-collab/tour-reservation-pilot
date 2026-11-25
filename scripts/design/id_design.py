"""ID 設計の原本（docs/design/ID設計.xlsx）を使う作業をまとめたコマンド。人が実行する（openpyxl が要る）。

    python3 scripts/design/id_design.py list       # 機能一覧と、もとになる設計書の行から書類一覧を作り直す（番号は保ち、新しい書類だけ末尾の番号を振る）
    python3 scripts/design/id_design.py scaffold   # 書類一覧で「書く」にした書類のうち、まだないものの設計書ファイルを作る（見出しだけのひな形）
    python3 scripts/design/id_design.py progress   # 進捗・網羅状況のシートを作り直す（先に git fetch。統合先のブランチと比べて完了かを決める）
    python3 scripts/design/id_design.py export     # 書き出し（ID設計.md）を作る。--check なら食い違いを確かめるだけ
    python3 scripts/design/id_design.py paint      # 誰が埋める列かを見出しの色で示し、凡例のシートを作る（list・progress でも行う）
    オプション: --design <設計書のフォルダ>（既定 docs/design）
              --base <比べるブランチ>（progress 用。既定は環境変数 TAZUNA_BASE_BRANCH、なければ GitHub の既定のブランチ
              （origin/HEAD）、それもなければ origin/main。develop に統合する案件なら --base origin/develop）

list・scaffold・progress は最後に export も行う。書類一覧の番号は付けたら変えず、機能一覧から外れた書類も消さずに「廃止」にする。
どの書類が1枚ずつできるかは、書類の種類の「もと」で決まる（機能一覧の列か、設計書の見出しの行。テーブル設計書は S-20 のテーブル一覧の行ごと）。
書類の種類の「状態」が「廃止」（型でやめた）か「使わない」（この案件で作らないと決めた）の種類は、書類一覧に作らない。
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog  # noqa: E402

ROOT = os.environ.get("TAZUNA_ROOT") or os.getcwd()

# 書類の種類の「もと」（何が決まると、その書類が1枚ずつできるか）
#   空                … システムに1つ（最初の list からある）
#   機能一覧:<列>      … 機能一覧のその列に書いた名前ごと（機能一覧:機能 は機能ごと）
#   <書類ID>/<設計項目> … その書類のその見出しの行ごと。行の先頭の英字の名前を書類の名前にする（例 S-20/D-05020 テーブル一覧）
# 「もと」が空の書類の種類は、古い Excel のために「作る単位」から決める
UNIT = [("システムに1つ", ""), ("テーブルごと", "S-20/D-05020"), ("画面ごと", "機能一覧:画面"), ("ジョブごと", "機能一覧:ジョブ"),
        ("外部IFごと", "機能一覧:IF"), ("帳票", "機能一覧:帳票"), ("機能ごと", "機能一覧:機能")]
SOURCE_RE = re.compile(r"^(S-\d{2})/(D-\d{5})$")
NAME_HEAD_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)")


def source_of(t):
    s = (t.get("もと") or "").strip()
    if s:
        return s
    for prefix, src in UNIT:
        if (t.get("作る単位") or "").startswith(prefix):
            return src
    return ""


def source_names(folder, doc, item):
    """設計書 doc（すべての書類実体）の見出し item の行の先頭の名前。[(名前, 行ID)]（書いた順、重複なし）"""
    out, seen = [], set()
    for inst, name in sorted(catalog.design_files(folder).items()):
        if not inst.startswith(doc + "-"):
            continue
        _, lines, _ = catalog.parse_design(open(os.path.join(folder, name), encoding="utf-8").read())
        for _, n, text, under in lines:
            m = NAME_HEAD_RE.match(text or "")
            if under == item and n and m and not text.startswith("（廃止）") and m.group(1) not in seen:
                seen.add(m.group(1))
                out.append((m.group(1), catalog.line_id(inst, item, n)))
    return out


def derive(data, design=None):
    """機能一覧と、もとになる設計書の行から、あるべき書類実体を作る。[(書類ID, 名前, [機能の処理設計書の名前...])]
    テーブル設計書は S-20 データモデル設計書の「テーブル一覧」の行ごとに作り、機能は持たない（テーブルと機能のつながりは、処理設計書の CRUD の行）"""
    design = design or os.path.join(ROOT, "docs", "design")
    out = []
    funcs = data["機能一覧"]
    for t in data["書類の種類"]:
        if (t.get("状態") or "").strip() in ("廃止", "使わない"):
            continue
        doc, src = t["書類ID"], source_of(t)
        center = (t.get("役割") or "").strip() == "機能の中心"
        m = SOURCE_RE.match(src)
        if not src:
            out.append((doc, t["書類名"], []))
        elif m:
            out += [(doc, name, []) for name, _ in source_names(design, m.group(1), m.group(2))]
        elif src == "機能一覧:機能":
            for f in funcs:
                out.append((doc, f["機能"], [] if center else [f["機能"]]))
        elif src.startswith("機能一覧:"):
            col, seen = src.split(":", 1)[1], {}
            for f in funcs:
                for name in catalog.split(f.get(col)):
                    seen.setdefault(name, []).append(f["機能"])
            out += [(doc, name, fs) for name, fs in seen.items()]
    return out


def cmd_list(data, design=None):
    old = {(r["書類ID"], r["名前"]): r for r in data["書類一覧"]}
    nums = {}
    for r in data["書類一覧"]:
        nums[r["書類ID"]] = max(nums.get(r["書類ID"], 0), int(r["書類実体ID"][-3:]))
    want = derive(data, design)
    # 機能の中心の書類（処理設計書など）の書類実体ID（機能の名前 → 書類実体ID）を先に決める
    rows, keys = {}, set()
    for doc, name, _ in want:
        key = (doc, name)
        keys.add(key)
        if key in old:
            rows[key] = dict(old[key])
            if rows[key]["作成"] == "廃止":
                rows[key]["作成"] = "書く"
        else:
            nums[doc] = nums.get(doc, 0) + 1
            rows[key] = {"書類実体ID": f"{doc}-{nums[doc]:03d}", "書類ID": doc, "名前": name, "作成": "書く", "理由": ""}
    centers = {t["書類ID"] for t in data["書類の種類"] if (t.get("役割") or "").strip() == "機能の中心"}
    state = {t["書類ID"]: (t.get("状態") or "").strip() for t in data["書類の種類"]}
    s22 = {name: r["書類実体ID"] for (doc, name), r in rows.items() if doc in centers}
    docname = {t["書類ID"]: t["書類名"] for t in data["書類の種類"]}
    for doc, name, fs in want:
        r = rows[(doc, name)]
        r["書類名"] = docname.get(doc, "")
        r["機能"] = "、".join(s22[f] for f in fs if f in s22)
    for key, r in old.items():  # 機能一覧から外れた書類は消さずに廃止にする
        if key not in keys:
            r = dict(r)
            r["作成"] = "廃止"
            why = {"廃止": "書類の種類を廃止した", "使わない": "この案件では使わない書類の種類にした"}
            src = {t["書類ID"]: source_of(t) for t in data["書類の種類"]}.get(key[0], "")
            gone = f"もと（{src}）から外れた" if SOURCE_RE.match(src) else "機能一覧から外れた"
            r["理由"] = r["理由"] or why.get(state.get(key[0]), gone)
            rows[key] = r
    data["書類一覧"] = sorted(rows.values(), key=lambda r: r["書類実体ID"])
    return data


# 列を誰が埋めるか。"*" はそのシートの残りの列
WHO = {
    "人": ("FFF2CC", "BF9000", "人が埋める・決める（案件で書く）"),
    "案件": ("E2EFDA", "548235", "型の値だが、案件で変えてよい（変えた理由を PR に書く。base-design-check で確かめる）"),
    "ツール": ("EDEDED", "808080", "ツールが作る。手で直さない（直しても作り直すと消える）"),
    "型": ("DDEBF7", "2F5597", "型（標準化チームが持つ）。案件では変えない。変えたいときは標準化チームに伝える"),
}
OWNER = {
    "機能一覧": {"*": "人"},
    "書類一覧": {"作成": "人", "理由": "人", "*": "ツール"},
    "進捗": {"*": "ツール"}, "網羅状況": {"*": "ツール"}, "集計": {"*": "ツール"},
    "書類の種類": {"状態": "案件", "もと": "案件", "*": "型"}, "記載項目": {"記載": "案件", "*": "型"},
    "振り分け表": {"*": "型"}, "振り分けルール": {"*": "型"}, "属性の判定基準": {"*": "型"},
}
LEGEND = "凡例"
COLS_TEXT = {  # 列の色が付く場所（凡例に書く）
    "人": "機能一覧の全列、書類一覧の「作成」「理由」",
    "案件": "書類の種類の「状態」（使う・使わない）と「もと」、記載項目の「記載」（必須・該当時）",
    "ツール": "書類一覧の「作成」「理由」以外、進捗・網羅状況・集計の全列",
    "型": "振り分け表・振り分けルール・属性の判定基準の全列、書類の種類の「状態」「もと」以外、記載項目の「記載」以外",
}
PROCESS_SHEET = "進め方"
PROCESS = [  # (段階, 順, やること, 誰が, 使うもの, 次へ進む目安)
    ("準備（ID 設計）", "1", "何を作るか決める。書類の種類の「状態」で、この案件で作らない種類を「使わない」にする。"
     "「もと」で、どの書類が何が決まると1枚ずつできるかを確かめる（下の表）", "案件リーダー", "書類の種類", "PR でマージ"),
    ("", "2", "何を書くか決める。記載項目の「記載」（必須・該当時）を案件に合わせる", "案件リーダー", "記載項目", "PR でマージ"),
    ("", "3", "機能一覧に、外部設計で決まっている範囲で、機能と画面・ジョブ・IF・帳票と説明を書く（全部そろうのを待たない）",
     "社員", "機能一覧", "—"),
    ("", "4", "書類一覧を作る。システムに1つの書類と、もとが決まっている書類が並ぶ。1枚ずつ「作成」（書く・書かない＋理由）を決める",
     "社員", "id_design.py list、書類一覧", "ID設計.xlsx と ID設計.md を PR でマージ"),
    ("", "5", "設計書のひな形を作る", "社員", "id_design.py scaffold", "—"),
    ("設計", "6", "共通の書類を書く（方式・画面共通・メッセージ・セキュリティ・コード定義など）。★ が出たら、共通の方針・機能に任せる旨・該当なし（理由）のどれかを先に書く",
     "社員・協力会社", "docs/design/、案内役", "必須の見出しが埋まる"),
    ("", "7", "データモデル設計書（S-20）でテーブル一覧（D-05020）を決める。マージしたら list と scaffold をやり直すと、テーブル設計書が1枚ずつできる",
     "社員・DBA", "S-20、id_design.py list・scaffold", "テーブル一覧を PR でマージ"),
    ("", "8", "テーブル一覧の1行ごとに DDL（db/schema/<テーブル>.sql）を書く。全列に説明、区分値は CHECK と設計書の行ID。テーブル設計書（S-16）には DDL に書けない決定だけを書く",
     "協力会社・DBA", "db/schema/、S-16", "Lint の「DDL がない」「一覧にない」が消える"),
    ("", "9", "機能の書類を書く（処理・画面・ジョブ・IF・帳票・テスト仕様）。CRUD にはテーブル一覧の名前を使う。画面などが増えたら機能一覧に足して 4 をやり直す",
     "社員・協力会社", "処理設計書ほか", "必須の見出しが埋まる"),
    ("", "10", "設計の PR をレビューしてマージする。食い違い・未定義・抜けはスキル base-design-review で見る。業務の正しさは人が見る",
     "社員", "base-design-review、review_pack.py", "承認してマージ。id_design.py progress で状態を確かめる"),
    ("転記", "11", "機能の書類がそろったら、要件・テスト仕様・作業一覧へ転記し、転記の PR で確かめてマージする", "社員",
     "transcribe.py", "進捗の「要転記」が消える"),
    ("実装", "12", "要件ごとに issue を作り（下書きは next.py --issue REQ-xxxxx）、Copilot か担当者に割り当てる", "案件リーダー",
     "next.py", "—"),
    ("", "13", "実装の PR を出す。本文に「対象要件:」、テストに行IDの @Tag、対応しない行は「未対応:」、設計書を根拠にした行は「設計書から:」",
     "Copilot・協力会社", "AGENTS.md、base-task-workflow", "CI が通る"),
    ("", "14", "PR レポートを見てレビューし、マージする", "社員", "PR レポート", "マージ"),
    ("ずっと", "15", "「次は何？」と案内役に聞き、日次レポートで止まっているもの・つながっていないものを見る。設計を変えるときは設計書から（6〜11）",
     "全員", "base-navigator、日次レポート", "—"),
]


def when_ready(src, cat_docs, items):
    """書類の種類の「もと」を、いつ書類ができるかの文にする"""
    m = SOURCE_RE.match(src)
    if not src:
        return "最初の list から（システムに1つ）"
    if m:
        doc = cat_docs.get(m.group(1), m.group(1))
        return f"{m.group(1)} {doc}の「{m.group(2)} {items.get(m.group(2), '')}」に行を書いて、list をやり直したとき（行ごとに1枚）"
    col = src.split(":", 1)[1]
    return "機能一覧に機能を書いて、list をやり直したとき（機能ごとに1枚）" if col == "機能" else \
        f"機能一覧の「{col}」に名前を書いて、list をやり直したとき（名前ごとに1枚）"


def process_sheet(wb):
    """進め方のシート（ID 設計から実装まで）を作り直す。前後関係の表は書類の種類のシートから作る"""
    from openpyxl.styles import Alignment, Font
    if PROCESS_SHEET in wb.sheetnames:
        del wb[PROCESS_SHEET]
    ws = wb.create_sheet(PROCESS_SHEET, 1 if LEGEND in wb.sheetnames else 0)
    bold, wrap = Font(bold=True), Alignment(wrap_text=True, vertical="top")
    ws.append(["ID 設計・設計・転記・実装の進め方（id_design.py が作る。手で直さない）"])
    ws.append([])
    ws.append(["段階", "順", "やること", "誰が", "使うもの", "次へ進む目安"])
    head = ws.max_row
    for row in PROCESS:
        ws.append(list(row))
    ws.append([])
    ws.append(["書類ができる前後関係（書類の種類の「もと」から作る）"])
    ws.cell(ws.max_row, 1).font = bold
    ws.append(["書類ID", "書類名", "もと", "書類一覧にできるとき", "状態", ""])
    head2 = ws.max_row
    kinds = [dict(zip([c.value for c in wb["書類の種類"][1]], r)) for r in wb["書類の種類"].iter_rows(min_row=2, values_only=True)] \
        if "書類の種類" in wb.sheetnames else []
    kinds = [k for k in kinds if k.get("書類ID")]
    names = {k["書類ID"]: k.get("書類名") or "" for k in kinds}
    items = {r[0]: r[2] for r in wb["振り分け表"].iter_rows(min_row=2, values_only=True) if r and r[0]} \
        if "振り分け表" in wb.sheetnames else {}
    for k in kinds:
        src = source_of({key: (v if isinstance(v, str) else "") for key, v in k.items()})
        ws.append([k["書類ID"], names[k["書類ID"]], src or "—", when_ready(src, names, items), k.get("状態") or ""])
    for r in (1, head, head2):
        for c in range(1, 7):
            ws.cell(r, c).font = bold
    for col, width in zip("ABCDEF", (14, 10, 60, 16, 28, 34)):
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=head):
        for c in row:
            c.alignment = wrap
    ws.freeze_panes = ws.cell(head + 1, 1)



def paint(wb):
    """各シートの1行目（列の見出し）の色で、誰が埋める列かを示す。人が書く列は入力欄も塗る。凡例のシートを先頭に置く"""
    from openpyxl.styles import Font, PatternFill
    fill = {k: PatternFill("solid", fgColor="FF" + v[0], bgColor="FF" + v[0]) for k, v in WHO.items()}
    for sheet, rule in OWNER.items():
        if sheet not in wb.sheetnames:
            continue
        ws = wb[sheet]
        last = max(ws.max_row, 200 if rule.get("*") == "人" or "人" in rule.values() else ws.max_row)
        for c in range(1, ws.max_column + 1):
            name = ws.cell(1, c).value
            if name in (None, ""):
                continue
            who = rule.get(name, rule["*"])
            ws.cell(1, c).fill = fill[who]
            ws.cell(1, c).font = Font(bold=True)
            if who == "人":  # 入力欄は空の行まで塗る
                for r in range(2, last + 1):
                    ws.cell(r, c).fill = fill[who]
        ws.sheet_properties.tabColor = None  # シートのタブには色を付けない（列の色と意味が二重になるため）
        ws.freeze_panes = "A2"
    if LEGEND in wb.sheetnames:
        del wb[LEGEND]
    ws = wb.create_sheet(LEGEND, 0)
    bold = Font(bold=True)
    ws.append(["各シートの1行目（列の見出し）の色で、その列を誰が埋めるかを示す。人が書く列は、下の入力欄も同じ色にしている。"])
    ws.append([])
    ws.append(["色", "意味", "この色の列"])
    head = ws.max_row
    for key in ["人", "案件", "ツール", "型"]:
        ws.append([key, WHO[key][2], COLS_TEXT[key]])
        ws.cell(ws.max_row, 1).fill = fill[key]
    ws.append([])
    ws.append(["進め方", f"「{PROCESS_SHEET}」のシートを見る（ID 設計から実装までの手順と、書類ができる前後関係）", ""])
    for r in (head, ws.max_row):
        for c in range(1, 4):
            ws.cell(r, c).font = bold
    ws.cell(1, 1).font = bold
    for col, width in zip("ABC", (8, 80, 60)):
        ws.column_dimensions[col].width = width
    from openpyxl.styles import Alignment
    for row in ws.iter_rows(min_row=head):
        for c in row[1:3]:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.sheet_properties.tabColor = None
    process_sheet(wb)
    wb.active = wb.sheetnames.index("機能一覧") if "機能一覧" in wb.sheetnames else 0


def write_sheet(path, sheet, cols, rows):
    from openpyxl import load_workbook
    wb = load_workbook(path)
    ws = wb[sheet]
    for c, name in enumerate(cols, 1):
        ws.cell(1, c, name)
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)
    for r in rows:
        ws.append([r.get(c, "") for c in cols])
    paint(wb)
    wb.save(path)


def cmd_scaffold(folder, cat):
    files = catalog.design_files(folder)
    made = []
    for inst, r in sorted(cat.instances.items()):
        if r["作成"] != "書く" or inst in files:
            continue
        doc = r["書類ID"]
        md = [f"# {inst} {r['書類名']}：{r['名前']}", "",
              "> 見出しの下に、1行に1つの決定事項を「- [番号] 本文」で書く。番号は見出しの中で 1, 2, 3 と付け、"
              "後から足すときはその見出しの末尾の続きにする（振り直さない）。消すときは行を残して「（廃止）」と書く。"
              "書くことがない見出しには「該当なし（理由）」と書く。順序が大事なときは、順序を決める見出し"
              "（処理シーケンス・優先順位など）に「D-04001 の [1] → [3] の順」のように書く。"
              "図（Mermaid など）や表は、それを説明する行の直下に2文字字下げして書く（行と一緒に転記される）。", ""]
        for iid, rec in sorted(cat.records.get(doc, {}).items()):
            note = f"（{rec['記載']}）" + (f" {rec['この書類で書くこと']}" if rec["この書類で書くこと"] else "")
            md += [f"## {iid} {rec['設計項目']}", "", f"<!-- {note} -->", ""]
        name = catalog.file_name(inst, r["名前"])
        with open(os.path.join(folder, name), "w", encoding="utf-8") as fp:
            fp.write("\n".join(md).rstrip("\n") + "\n")
        made.append(name)
    return made


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)


def open_pr_files():
    """開いている PR が触っているファイル（gh があるときだけ）"""
    r = subprocess.run(["gh", "pr", "list", "--state", "open", "--json", "files", "--limit", "100"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    import json
    return {f["path"] for pr in json.loads(r.stdout or "[]") for f in pr.get("files", [])}


def base_branch(explicit=None):
    """進捗で「完了」を決めるときに比べるブランチ"""
    for cand in (explicit, os.environ.get("TAZUNA_BASE_BRANCH")):
        if cand:
            return cand
    head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if head.returncode == 0 and head.stdout.strip():
        return head.stdout.strip()
    for cand in ("origin/main", "origin/master", "main", "master"):
        if git("rev-parse", "--verify", "-q", cand).returncode == 0:
            return cand
    return "main"


def cmd_progress(folder, cat, base=None):
    import transcribe
    files = catalog.design_files(folder)
    base = base_branch(base)
    print("比べるブランチ:", base)
    prs = open_pr_files()
    trans = transcribe.status(folder, ROOT)
    tests = test_refs()
    defined = defined_reqs()
    prog, cover = [], []
    for inst, r in sorted(cat.instances.items()):
        doc = r["書類ID"]
        need = {i for i, rec in cat.records.get(doc, {}).items() if rec["記載"] == "必須"}
        name = files.get(inst)
        heads, lines, na = ([], [], set())
        if name:
            heads, lines, na = catalog.parse_design(open(os.path.join(folder, name), encoding="utf-8").read())
        live = [l for l in lines if l[1] and not l[2].startswith("（廃止）")]
        written = {}
        for _, _, _, under in live:
            written[under] = written.get(under, 0) + 1
        done_need = {i for i in need if i in written or i in na}
        if r["作成"] in ("書かない", "廃止"):
            state = r["作成"]
        elif not live:
            state = "未着手"
        else:
            rel = os.path.relpath(os.path.join(folder, name), ROOT)
            same = git("diff", "--quiet", base, "--", rel).returncode == 0 and git("ls-files", "--error-unmatch", rel).returncode == 0
            if same:
                state = "完了" if done_need == need else "必須不足"
            elif prs is not None and rel in prs:
                state = "レビュー中"
            else:
                state = "執筆中"
        req = f"REQ-{doc[2:]}{inst[-3:]}"
        req = req if req in defined else ""
        prog.append({"書類実体ID": inst, "名前": r["名前"], "機能": r["機能"], "状態": state,
                     "必須の見出し": f"{len(done_need)}/{len(need)}", "行": str(len(live)),
                     "転記": trans.get(inst, "—"),
                     "要件": req, "テスト": ("あり" if req in tests else "未実装") if req else ""})
        if r["作成"] in ("書かない", "廃止"):
            continue
        for iid, rec in sorted(cat.records.get(doc, {}).items()):
            st = f"書いた（{written[iid]}行）" if iid in written else ("該当なし" if iid in na else "未記入")
            cover.append({"書類実体ID": inst, "名前": r["名前"], "項番": iid, "設計項目": rec["設計項目"], "記載": rec["記載"], "状況": st})
    return prog, cover


def defined_reqs():
    found = set()
    d = os.path.join(ROOT, "docs", "requirements")
    for n in os.listdir(d) if os.path.isdir(d) else []:
        if n.endswith(".md"):
            found |= set(re.findall(r"^##\s+(REQ-\d+)", open(os.path.join(d, n), encoding="utf-8").read(), re.M))
    return found


def test_refs():
    found = set()
    for d in ("src/test", "tests"):
        p = os.path.join(ROOT, d)
        for dirpath, _, names in os.walk(p):
            for n in names:
                try:
                    found |= set(re.findall(r"REQ-\d+", open(os.path.join(dirpath, n), encoding="utf-8", errors="ignore").read()))
                except OSError:
                    pass
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["list", "scaffold", "progress", "export", "paint"])
    ap.add_argument("--design", default=os.path.join(ROOT, "docs", "design"))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--base", default=None)
    a = ap.parse_args()
    xlsx = os.path.join(a.design, catalog.XLSX)
    snap = os.path.join(a.design, catalog.SNAPSHOT)
    data = catalog.read_excel(xlsx)

    if a.command == "export" and a.check:
        current = open(snap, encoding="utf-8").read() if os.path.exists(snap) else None
        if current != catalog.render_snapshot(data):
            print(f"ERROR [COMMON-009] {os.path.relpath(snap, ROOT)}\n  内容: ID設計.md が ID設計.xlsx と食い違っています\n"
                  "  理由: PR では書き出しの差分でレビューし、Lint と転記ツールも書き出しを読むためです\n"
                  "  修正: python3 scripts/design/id_design.py export を実行して、ID設計.md も一緒にコミットしてください\n"
                  "  参照: scripts/design/catalog.py", file=sys.stderr)
            return 1
        return 0

    if a.command == "paint":
        from openpyxl import load_workbook
        wb = load_workbook(xlsx)
        paint(wb)
        wb.save(xlsx)
        print("色を付けました（凡例のシート）")
        return 0
    if a.command == "list":
        data = cmd_list(data, a.design)
        write_sheet(xlsx, "書類一覧", catalog.TABLES[1][1], data["書類一覧"])
        print(f"書類一覧: {len(data['書類一覧'])} 件")
    elif a.command == "scaffold":
        for name in cmd_scaffold(a.design, catalog.Catalog(data)):
            print("ひな形:", name)
    elif a.command == "progress":
        prog, cover = cmd_progress(a.design, catalog.Catalog(data), a.base)
        write_sheet(xlsx, "進捗", ["書類実体ID", "名前", "機能", "状態", "必須の見出し", "行", "転記", "要件", "テスト"], prog)
        write_sheet(xlsx, "網羅状況", ["書類実体ID", "名前", "項番", "設計項目", "記載", "状況"], cover)
        from collections import Counter
        print("進捗:", dict(Counter(p["状態"] for p in prog)))
    catalog.write_snapshot(catalog.read_excel(xlsx), snap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
