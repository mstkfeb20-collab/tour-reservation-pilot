"""ID 設計の原本（docs/design/ID設計.xlsx）を使う作業をまとめたコマンド。人が実行する（openpyxl が要る）。

    python3 scripts/design/id_design.py list       # 機能一覧から書類一覧を作り直す（番号は保ち、新しい書類だけ末尾の番号を振る）
    python3 scripts/design/id_design.py scaffold   # 書類一覧で「書く」にした書類のうち、まだないものの設計書ファイルを作る（見出しだけのひな形）
    python3 scripts/design/id_design.py progress   # 進捗・網羅状況のシートを作り直す
    python3 scripts/design/id_design.py export     # 書き出し（ID設計.md）を作る。--check なら食い違いを確かめるだけ
    オプション: --design <設計書のフォルダ>（既定 docs/design）

list・scaffold・progress は最後に export も行う。書類一覧の番号は付けたら変えず、機能一覧から外れた書類も消さずに「廃止」にする。
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog  # noqa: E402

ROOT = os.environ.get("TAZUNA_ROOT") or os.getcwd()

# 書類の種類の「作る単位」→ 機能一覧のどの列から書類実体を作るか
UNIT = [("システムに1つ", None), ("テーブルごと", "テーブル"), ("画面ごと", "画面"), ("ジョブごと", "ジョブ"),
        ("外部IFごと", "IF"), ("帳票", "帳票"), ("機能ごと", "機能")]


def unit_column(unit):
    for prefix, col in UNIT:
        if unit.startswith(prefix):
            return col
    return None


def derive(data):
    """機能一覧から、あるべき書類実体を作る。[(書類ID, 名前, [機能の処理設計書の名前...])]（機能一覧の順）"""
    out = []
    funcs = data["機能一覧"]
    for t in data["書類の種類"]:
        doc, col = t["書類ID"], unit_column(t["作る単位"])
        if col is None:
            out.append((doc, t["書類名"], []))
        elif col == "機能":
            for f in funcs:
                out.append((doc, f["機能"], [] if doc == "S-22" else [f["機能"]]))
        else:
            seen = {}
            for f in funcs:
                for name in catalog.split(f.get(col)):
                    seen.setdefault(name, [])
                    if col != "テーブル":  # テーブル定義書は共通設計なので機能を持たない
                        seen[name].append(f["機能"])
            out += [(doc, name, fs) for name, fs in seen.items()]
    return out


def cmd_list(data):
    old = {(r["書類ID"], r["名前"]): r for r in data["書類一覧"]}
    nums = {}
    for r in data["書類一覧"]:
        nums[r["書類ID"]] = max(nums.get(r["書類ID"], 0), int(r["書類実体ID"][-3:]))
    want = derive(data)
    # 処理設計書の書類実体ID（機能の名前 → S-22-nnn）を先に決める
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
    s22 = {name: r["書類実体ID"] for (doc, name), r in rows.items() if doc == "S-22"}
    docname = {t["書類ID"]: t["書類名"] for t in data["書類の種類"]}
    for doc, name, fs in want:
        r = rows[(doc, name)]
        r["書類名"] = docname.get(doc, "")
        r["機能"] = "、".join(s22[f] for f in fs if f in s22)
    for key, r in old.items():  # 機能一覧から外れた書類は消さずに廃止にする
        if key not in keys:
            r = dict(r)
            r["作成"], r["理由"] = "廃止", r["理由"] or "機能一覧から外れた"
            rows[key] = r
    data["書類一覧"] = sorted(rows.values(), key=lambda r: r["書類実体ID"])
    return data


def write_sheet(path, sheet, cols, rows):
    from openpyxl import load_workbook
    wb = load_workbook(path)
    ws = wb[sheet]
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)
    for r in rows:
        ws.append([r.get(c, "") for c in cols])
    wb.save(path)


def cmd_scaffold(folder, cat):
    files = catalog.design_files(folder)
    made = []
    for inst, r in sorted(cat.instances.items()):
        if r["作成"] != "書く" or inst in files:
            continue
        doc = r["書類ID"]
        md = [f"# {inst} {r['書類名']}：{r['名前']}", "",
              "> 見出しの下に、1行に1つの決定事項を「- 行ID 本文」で書く。行IDはこのファイルの末尾の次の番号（例 "
              f"{inst}-001）。書くことがない見出しには「該当なし（理由）」と書く。", ""]
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


def cmd_progress(folder, cat):
    import transcribe
    files = catalog.design_files(folder)
    base = "origin/main" if git("rev-parse", "--verify", "-q", "origin/main").returncode == 0 else "main"
    prs = open_pr_files()
    trans = transcribe.status(folder, ROOT)
    tests = test_refs()
    prog, cover = [], []
    for inst, r in sorted(cat.instances.items()):
        doc = r["書類ID"]
        need = {i for i, rec in cat.records.get(doc, {}).items() if rec["記載"] == "必須"}
        name = files.get(inst)
        heads, lines, na = ([], [], set())
        if name:
            heads, lines, na = catalog.parse_design(open(os.path.join(folder, name), encoding="utf-8").read())
        live = [l for l in lines if not l[2].startswith("（廃止）")]
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
        req = f"REQ-{doc[2:]}{inst[-3:]}" if doc == "S-22" else ""
        prog.append({"書類実体ID": inst, "名前": r["名前"], "機能": r["機能"], "状態": state,
                     "必須の見出し": f"{len(done_need)}/{len(need)}", "行": str(len(live)),
                     "転記": trans.get(inst, "—"),
                     "要件": req, "テスト": ("あり" if req in tests else "未実装") if req and trans.get(inst) in ("済", "要転記") else ""})
        if r["作成"] in ("書かない", "廃止"):
            continue
        for iid, rec in sorted(cat.records.get(doc, {}).items()):
            st = f"書いた（{written[iid]}行）" if iid in written else ("該当なし" if iid in na else "未記入")
            cover.append({"書類実体ID": inst, "名前": r["名前"], "項番": iid, "設計項目": rec["設計項目"], "記載": rec["記載"], "状況": st})
    return prog, cover


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
    ap.add_argument("command", choices=["list", "scaffold", "progress", "export"])
    ap.add_argument("--design", default=os.path.join(ROOT, "docs", "design"))
    ap.add_argument("--check", action="store_true")
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

    if a.command == "list":
        data = cmd_list(data)
        write_sheet(xlsx, "書類一覧", catalog.TABLES[1][1], data["書類一覧"])
        print(f"書類一覧: {len(data['書類一覧'])} 件")
    elif a.command == "scaffold":
        for name in cmd_scaffold(a.design, catalog.Catalog(data)):
            print("ひな形:", name)
    elif a.command == "progress":
        prog, cover = cmd_progress(a.design, catalog.Catalog(data))
        write_sheet(xlsx, "進捗", ["書類実体ID", "名前", "機能", "状態", "必須の見出し", "行", "転記", "要件", "テスト"], prog)
        write_sheet(xlsx, "網羅状況", ["書類実体ID", "名前", "項番", "設計項目", "記載", "状況"], cover)
        from collections import Counter
        print("進捗:", dict(Counter(p["状態"] for p in prog)))
    catalog.write_snapshot(catalog.read_excel(xlsx), snap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
