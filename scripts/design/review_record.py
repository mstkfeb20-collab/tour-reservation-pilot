"""設計書の点検（スキル base-design-review）の結果を記録し、レビューを始めてよいかを確かめる（COMMON-011）。

    python3 scripts/design/review_record.py stamp   # 点検の結果を書いた後に実行する。今の設計書の指紋を記録に付ける
    python3 scripts/design/review_record.py check   # Lint から呼ぶ

点検はレビューではない。書き手が人のレビューの前に使う道具で、件数は品質の指標にしない。
ここで確かめるのは「人のレビューを始めてよいか」（レビュー開始条件）だけ:
  - 記録（docs/review/設計書の点検.tsv）が今の設計書に対するものである（指紋が一致する）
  - 止める種別（食い違い・未定義・場合分けの抜け・書式の解釈）の行は、直して点検し直すか、「扱い」に「残す: 理由」がある
  - 質問の行は、「扱い」に「issue: #番号」がある（業務の決定は issue で追う）

記録の形（TSV。1行目と2行目は stamp が書く）:
  # 点検した設計書の指紋: <指紋>
  種別	根拠の行ID	指摘	扱い

止めるのは PR で設計書（docs/design/S-*.md）を変えたときだけ。ドラフトの PR と手元では警告にする（書いている途中は止めない）。
"""
import argparse
import hashlib
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog  # noqa: E402

RECORD = "docs/review/設計書の点検.tsv"
HEAD = "# 点検した設計書の指紋: "
COLUMNS = ["種別", "根拠の行ID", "指摘", "扱い"]
BLOCKING = ("食い違い", "未定義", "場合分けの抜け", "書式の解釈")
REF = ".github/skills/base-design-review/SKILL.md"


def fingerprint(design):
    """設計書（S-*.md）の中身の指紋。ID設計.md・Excel は含めない（機能一覧を直しただけで点検し直しにならないように）"""
    h = hashlib.sha1()
    for inst, name in sorted(catalog.design_files(design).items()):
        h.update(name.encode())
        with open(os.path.join(design, name), "rb") as fp:
            h.update(fp.read())
    return h.hexdigest()[:12]


def read_record(path):
    """(指紋 or None, [行の辞書])"""
    if not os.path.exists(path):
        return None, []
    fp_, rows = None, []
    with open(path, encoding="utf-8") as fp:
        for raw in fp.read().splitlines():
            if raw.startswith(HEAD):
                fp_ = raw[len(HEAD):].strip()
                continue
            if not raw.strip() or raw.startswith("#"):
                continue
            cols = raw.split("\t")
            if cols[0] == COLUMNS[0]:
                continue
            cols += [""] * (len(COLUMNS) - len(cols))
            rows.append(dict(zip(COLUMNS, [c.strip() for c in cols])))
    return fp_, rows


def stamp(root, design):
    path = os.path.join(root, RECORD)
    if not os.path.exists(path):
        sys.exit(f"{RECORD} がありません。スキル base-design-review の結果（TSV）を先に保存してください")
    with open(path, encoding="utf-8") as fp:
        lines = [l for l in fp.read().splitlines() if not l.startswith(HEAD)]
    if not lines or not lines[0].startswith(COLUMNS[0]):
        lines.insert(0, "\t".join(COLUMNS))
    with open(path, "w", encoding="utf-8") as fp:
        fp.write("\n".join([HEAD + fingerprint(design)] + lines) + "\n")
    print(f"{RECORD} に今の設計書の指紋を付けました。設計書と一緒にコミットしてください")
    return 0


def design_changed(root, base):
    """PR で設計書（docs/design/S-*.md）を変えたか"""
    try:
        out = subprocess.run(["git", "-C", root, "diff", "--name-only", f"{base}...HEAD", "--", "docs/design"],
                             capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True  # 比べられないときは、変えたものとして扱う
    return any(os.path.basename(p).startswith("S-") and p.endswith(".md") for p in out.splitlines())


def check(root, design):
    files = catalog.design_files(design)
    if not files:
        return 0
    in_pr = os.environ.get("TAZUNA_IS_PR") == "1"
    draft = os.environ.get("TAZUNA_PR_DRAFT", "").lower() in ("1", "true")
    base = os.environ.get("DESIGN_BASE_REF", "")
    strict = in_pr and not draft and (not base or design_changed(root, base))
    if in_pr and not strict and not draft:
        return 0  # 設計書を変えていない PR（実装・転記など）は見ない
    problems = []
    fp_, rows = read_record(os.path.join(root, RECORD))
    if fp_ is None:
        problems.append(("点検の記録がありません",
                         "人のレビューは、形式・噛み合いの問題をスキルで先につぶしてから始めます",
                         f"スキル base-design-review で点検し、結果の表を {RECORD} に保存して "
                         "python3 scripts/design/review_record.py stamp を実行してください"))
    elif fp_ != fingerprint(design):
        problems.append(("点検の後に設計書が変わっています",
                         "記録は、点検したときの設計書に対するものです。直した後の設計書は点検されていません",
                         "スキル base-design-review で点検し直し、記録を書き直して stamp を実行してください"
                         "（前回の「扱い」は、同じ種別・根拠の行には引き継ぐ）"))
    for r in rows:
        kind, how = r["種別"], r["扱い"]
        where = f"{r['根拠の行ID']}（{kind}）"
        if kind in BLOCKING and not how.startswith("残す"):
            problems.append((f"{where} {r['指摘']}",
                             f"「{kind}」は、残したまま実装に進むと手戻りになります",
                             "設計書を直して点検し直すか、直さないなら「扱い」の列に「残す: 理由」と書いてください"))
        if kind == "質問" and "issue" not in how:
            problems.append((f"{where} {r['指摘']}",
                             "質問は業務で決めることです。issue にしないと、決まるまで追えません",
                             "スキルが出した下書きで issue を作り、「扱い」の列に「issue: #番号」と書いてください"))
    for what, why, fix in problems:
        if strict:
            print(f"ERROR [COMMON-011] {RECORD}\n  内容: {what}\n  理由: {why}\n  修正: {fix}\n  参照: {REF}", file=sys.stderr)
        else:
            print(f"WARN  [COMMON-011] {RECORD} : {what}（レビューを頼む前に直す）", file=sys.stderr)
    return 1 if strict and problems else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["stamp", "check"])
    ap.add_argument("--root", default=os.environ.get("TAZUNA_ROOT") or os.getcwd())
    a = ap.parse_args()
    design = os.path.join(a.root, "docs", "design")
    if not os.path.isdir(design) or catalog.load(design) is None:
        return 0
    return stamp(a.root, design) if a.command == "stamp" else check(a.root, design)


if __name__ == "__main__":
    sys.exit(main())
