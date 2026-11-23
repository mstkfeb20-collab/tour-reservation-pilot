"""ID 設計書（docs/design/*.md）の置き場所と番号を検査する。design-docs.sh から呼ぶ。

    python3 scripts/lint/common/design_docs.py [設計書のフォルダ] [--base <git ref>]

検査すること（どれも読むだけで判定できる構造の検査。中身が正しい見出しに書かれているかはスキル base-design-check が見る）:
  1. ファイル名が「書類実体ID_名前.md」（例 S-21-002_予約入力.md）で、書類IDがドキュメント体系にある
  2. 見出し「## D-ccsss 設計項目名」の項番と名前がカタログと一致し、その書類の記載項目に入っている
  3. 行「- 行ID 本文」の行IDが「書類実体ID-通し番号3桁」で、ファイル名の書類実体IDと一致し、重複しない
  4. 行がどれかの見出しの下にある
  6. ID設計.xlsx の書類一覧に、すべての書類実体が載っていて、ファイル名が一覧の名前と合う
  7. 機能別設計の書類（処理設計書以外）は、書類一覧の「機能」に処理設計書が入っている
  警告だけ出すこと: 書類一覧で「書く」なのにまだファイルがない（id_design.py scaffold で作れる）
  5. --base を付けたとき: base にあった行IDが消えていない（廃止は消さずに「（廃止）」と書く）
  警告だけ出すこと: 書類の「必須」の記載項目に見出しがない
カタログ: 設計書のフォルダの ID設計.md（ID設計.xlsx の書き出し。scripts/design/catalog.py）
"""
import os
import re
import subprocess
import sys

ROOT = os.environ.get("TAZUNA_ROOT") or os.getcwd()
REF = "docs/design/ID設計.xlsx（書き出しは ID設計.md）"
errors = 0


def error(where, what, why, fix, ref=REF):
    global errors
    errors += 1
    print(f"ERROR [COMMON-007] {where}\n  内容: {what}\n  理由: {why}\n  修正: {fix}\n  参照: {ref}", file=sys.stderr)


def warn(where, what):
    print(f"WARN  [COMMON-007] {where} : {what}", file=sys.stderr)


FILE_RE = re.compile(r"^(S-\d{2})-(\d{3})_.+\.md$")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "design"))
import catalog  # noqa: E402


def main():
    args = sys.argv[1:]
    base = None
    if "--base" in args:
        i = args.index("--base")
        base = args[i + 1]
        del args[i:i + 2]
    folder = args[0] if args else os.path.join(ROOT, "docs", "design")
    if not os.path.isdir(folder):
        return 0  # ID 設計書を置いていない案件では何もしない
    cat = catalog.load(folder)
    if cat is None:
        if catalog.design_files(folder):
            error(os.path.relpath(os.path.join(folder, catalog.SNAPSHOT), ROOT), "ID設計.md（ID設計.xlsx の書き出し）がありません",
                  "書類と設計項目の一覧がないと、置き場所を検査できません",
                  "python3 scripts/design/id_design.py export を実行してください")
            return 1
        return 0
    items, docs, records = cat.items, cat.docs, cat.records

    seen = {}
    files = {}
    reg_rel = os.path.relpath(os.path.join(folder, catalog.XLSX), ROOT) + " の書類一覧"
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md") or name.lower() == "readme.md" or name == catalog.SNAPSHOT:
            continue
        path = os.path.join(folder, name)
        rel = os.path.relpath(path, ROOT)
        m = FILE_RE.match(name)
        if not m:
            error(rel, f"ファイル名 '{name}' が「書類実体ID_名前.md」になっていません",
                  "ファイル名の書類実体IDから、どの書類か（共通設計か機能別設計か）と行IDを決めるためです",
                  "S-21-002_予約入力.md のように、書類ID（S-xx）と3桁の番号を付けてください")
            continue
        doc, inst = m.group(1), f"{m.group(1)}-{m.group(2)}"
        files[inst] = (rel, name)
        if doc not in docs:
            error(rel, f"書類ID {doc} がドキュメント体系にありません",
                  "書類ごとに書いてよい設計項目が決まっているためです",
                  "ドキュメント体系の書類IDを使ってください。新しい書類の種類が要るなら ID設計.xlsx の「書類の種類」「記載項目」に足してください")
            continue
        allowed = records.get(doc, {})
        with open(path, encoding="utf-8") as fp:
            body = fp.read()
        heads, lines, _ = catalog.parse_design(body)

        for n, iid, label in heads:
            where = f"{rel}:{n}"
            if iid is None:
                error(where, f"見出し '## {label}' が「## D-ccsss 設計項目名」になっていません",
                      "見出しの項番から、行の振り分け先を機械的に決めるためです",
                      "ID設計.md の「設計項目」の項番と名前で見出しを書いてください")
            elif iid not in items:
                error(where, f"項番 {iid} がカタログにありません",
                      "カタログにない項目は振り分け先が決まりません",
                      "ID設計.md の「設計項目」の項番を使ってください。足りない項目は ID設計.xlsx の振り分け表に足してください")
            elif items[iid]["設計項目"] != label:
                error(where, f"項番 {iid} の名前が違います（'{label}'、カタログでは '{items[iid]['設計項目']}'）",
                      "項番と名前がずれると、どちらが正しいか分からなくなります",
                      f"'## {iid} {items[iid]['設計項目']}' に直してください")
            elif iid not in allowed:
                docs_for = sorted(d for d, rs in records.items() if iid in rs)
                error(where, f"{iid} {label} は {doc} {docs[doc]['書類名']} に書く項目ではありません",
                      "書類ごとに書く項目を決めておくと、共通か機能別かと置き場所が書類で決まります",
                      f"この項目は {'・'.join(docs_for)} に書いてください")

        for n, lid, text, under in lines:
            where = f"{rel}:{n}"
            if not re.fullmatch(rf"{re.escape(inst)}-\d{{3}}", lid):
                error(where, f"行ID '{lid}' が「{inst}-通し番号3桁」になっていません",
                      "行IDは書類実体IDとファイル内の通し番号で決め、人の判断を入れないためです",
                      f"{inst}-NNN の形にしてください。番号はファイルの末尾の次の番号です")
                continue
            if lid in seen:
                error(where, f"行ID {lid} が重複しています（{seen[lid]} にもある）",
                      "1つの行IDは1つの決定事項だけを指します",
                      "後から足した方の行に、ファイルの末尾の次の番号を付け直してください")
            seen[lid] = where
            if under is None:
                error(where, f"行 {lid} がどの見出しの下にもありません",
                      "見出しの設計項目が決まらないと、振り分け先が決まりません",
                      "当てはまる設計項目の見出しの下に移してください")

        have = {iid for _, iid, _ in heads}
        for iid, r in allowed.items():
            if r["記載"] == "必須" and iid not in have:
                warn(rel, f"必須の記載項目 {iid} {r['設計項目']} の見出しがありません")

    check_registry(cat, reg_rel, files, docs)

    if base:
        for lid in removed_ids(folder, base, seen):
            error(lid, f"行ID {lid} が {base} から消えています",
                  "行IDはチケットや転記先から参照されます。消すと参照が切れます",
                  "行を消さずに、本文を「（廃止）理由」や「（廃止）→ 移した先の行ID」にしてください")
    return 1 if errors else 0


def check_registry(cat, reg_rel, files, docs):
    """書類一覧（ID設計.xlsx）と、フォルダにある書類の突き合わせ"""
    why = "どの書類を作り、どの機能のものかを書類一覧1か所で決め、要件と作業一覧を機能ごとにまとめるためです"
    fix_list = "ID設計.xlsx の機能一覧を直して python3 scripts/design/id_design.py list を実行してください"
    for inst in cat.duplicates:
        error(reg_rel, f"書類実体ID {inst} が書類一覧で重複しています", why, fix_list)
    for inst, (rel, name) in sorted(files.items()):
        r = cat.instances.get(inst)
        if r is None:
            error(rel, f"{inst} が書類一覧にありません", why, fix_list)
        elif catalog.file_name(inst, r["名前"]) != name:
            error(rel, f"ファイル名が書類一覧の名前（{r['名前']}）と合いません",
                  "名前がずれると、どの書類か分からなくなります", f"ファイル名を {catalog.file_name(inst, r['名前'])} にしてください")
        elif r["作成"] == "書かない":
            warn(rel, f"書類一覧で「書かない」にした {inst} のファイルがあります")
    for inst, r in sorted(cat.instances.items()):
        doc = inst[:4]
        if doc not in docs:
            error(reg_rel, f"{inst} の書類ID {doc} がドキュメント体系にありません", why, fix_list)
            continue
        needs = docs[doc]["区分"] == "機能別設計" and doc != "S-22"
        if needs and not r["funcs"] and r["作成"] == "書く":
            error(reg_rel, f"{inst} {r['名前']} の「機能」が空です", why, "機能一覧で、この書類を使う機能の行に書いてから list を実行してください")
        for f in r["funcs"]:
            if f not in cat.instances:
                error(reg_rel, f"{inst} の機能 {f} が書類一覧にありません", why, fix_list)
        if r["作成"] == "書く" and inst not in files:
            warn(reg_rel, f"{inst} {r['名前']} はまだファイルがありません（python3 scripts/design/id_design.py scaffold で作れます）")


def removed_ids(folder, base, current):
    rel = os.path.relpath(folder, ROOT)
    try:
        names = subprocess.run(["git", "-C", ROOT, "ls-tree", "-z", "--name-only", f"{base}:{rel}"],
                               capture_output=True, text=True, check=True).stdout.split("\0")
    except subprocess.CalledProcessError:
        return []
    old = set()
    for name in names:
        if not catalog.FILE_RE.match(name):
            continue
        text = subprocess.run(["git", "-C", ROOT, "show", f"{base}:{rel}/{name}"],
                              capture_output=True, text=True).stdout
        old |= {lid for _, lid, _, _ in catalog.parse_design(text)[1] if lid}
    return sorted(old - set(current))


if __name__ == "__main__":
    sys.exit(main())
