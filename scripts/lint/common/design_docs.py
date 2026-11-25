"""ID 設計書（docs/design/*.md）の置き場所と番号を検査する。design-docs.sh から呼ぶ。

    python3 scripts/lint/common/design_docs.py [設計書のフォルダ] [--base <git ref>]

検査すること（どれも読むだけで判定できる構造の検査。中身が正しい見出しに書かれているかはスキル base-design-check が見る）:
  1. ファイル名が「書類実体ID_名前.md」（例 S-21-002_予約入力.md）で、書類IDがドキュメント体系にある
  2. 見出し「## D-ccsss 設計項目名」の項番と名前がカタログと一致し、その書類の記載項目に入っている
  3. 行は「- [番号] 本文」。番号は見出しの中で重複しない。行の ID は 書類実体／見出しの項番／番号（例 S-23-001/D-08002/2）
     他の行への参照（「D-04001 の [1] → [3]」「S-22-001/D-04001/1」）の参照先がある
  4. 行がどれかの見出しの下にある
  6. ID設計.xlsx の書類一覧に、すべての書類実体が載っていて、ファイル名が一覧の名前と合う
  7. 機能別設計の書類（処理設計書以外）は、書類一覧の「機能」に処理設計書が入っている
  警告だけ出すこと: 書類一覧で「書く」なのにまだファイルがない（id_design.py scaffold で作れる）
  5. 見出しの中の番号が 1 から最大まで欠けていない（欠番は行を消したか振り直した跡）
     --base を付けたとき（CI の PR）: base にあった行IDが消えていない（廃止は消さずに「（廃止）」と書く）
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
    pending = []  # (場所, 書いた書類実体, 参照)
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
        heads, lines, _, _, loose = catalog.scan_design(body)
        for n in loose:
            error(f"{rel}:{n}", "図や ``` のブロックがどの行にも付いていません",
                  "図は行と一緒に転記します。行に付いていない図は転記されず、どの決定の図か分からなくなります",
                  "図を説明する行「- [n] 本文」の直下に、2文字字下げして書いてください")

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

        local = {}
        for n, num, text, under in lines:
            where = f"{rel}:{n}"
            if under is None:
                error(where, "行がどの見出しの下にもありません",
                      "見出しの設計項目が決まらないと、振り分け先が決まりません",
                      "当てはまる設計項目の見出しの下に移してください")
                continue
            if num is None:
                error(where, f"行 '- {text[:30]}' が「- [番号] 本文」になっていません",
                      "行の ID は 書類／見出し／番号 で決まります。番号がないと、転記先やレビューから行を辿れません",
                      "見出しの中の末尾の次の番号を付けて「- [3] 本文」のように書いてください")
                continue
            lid = catalog.line_id(inst, under, num)
            if (under, num) in local:
                error(where, f"{under} の [{num}] が重複しています（{local[(under, num)]} にもある）",
                      "1つの番号は1つの決定事項だけを指します",
                      "後から足した方の行に、その見出しの中の末尾の次の番号を付けてください。番号は振り直さないでください")
            local[(under, num)] = where
            seen[lid] = where
            for r in catalog.refs(text):
                pending.append((where, inst, r))

        nums = {}
        for (under, num), _ in local.items():
            nums.setdefault(under, set()).add(int(num))
        for under, got in sorted(nums.items()):
            missing = [str(i) for i in range(1, max(got) + 1) if i not in got]
            if missing:
                error(rel, f"{under} の番号 [{'] ['.join(missing)}] がありません",
                      "番号は 1 から順に付け、行を消さずに「（廃止）」と書くので、欠番は行を消したか番号を振り直した跡です。"
                      "消した行を指していたレビューや転記先の参照が切れます",
                      "消した行を戻して本文を「（廃止）理由」にしてください。振り直した場合は元の番号に戻してください")

        have = {iid for _, iid, _ in heads}
        for iid, r in allowed.items():
            if r["記載"] == "必須" and iid not in have:
                warn(rel, f"必須の記載項目 {iid} {r['設計項目']} の見出しがありません")

    check_registry(cat, reg_rel, files, docs)
    check_gaps(cat, folder)

    for where, inst, (ri, item, num) in pending:
        target = catalog.line_id(ri or inst, item, num)
        if target not in seen:
            error(where, f"参照している {target} がありません",
                  "順序や関係を表す行が、存在しない行を指していると、意味が通りません",
                  "参照先の番号を直すか、参照先の行を書いてください（同じ書類の中は「D-04001 の [1] → [3]」、別の書類は「S-22-001/D-04001/1」）")

    if base:
        for lid in removed_ids(folder, base, seen):
            error(lid, f"行ID {lid} が {base} から消えています",
                  "行IDはチケットや転記先から参照されます。消すと参照が切れます",
                  "行を消さずに、本文を「（廃止）理由」や「（廃止）→ 移した先の行ID」にしてください")
    return 1 if errors else 0


def check_gaps(cat, folder):
    """★（共通の必須の見出しが空なのに、機能の書類が同じ設計項目を決めている）は警告。行が指すファイルがなければエラー"""
    import gaps
    w = gaps.written(folder, cat)
    files = catalog.design_files(folder)
    for inst, item, name, users in gaps.stars(folder, cat, w):
        rel = os.path.relpath(os.path.join(folder, files[inst]), ROOT)
        warn(rel, f"★ {item} {name} が空なのに、機能の書類（{'、'.join(sorted({u for u, _ in users}))}）が先に決めています。"
                  "共通の方針・機能に任せる旨・該当なし（理由）のどれかを書いてください")
    for lid, path, level in gaps.missing_refs(ROOT, folder, cat, w):
        inst = lid.split("/")[0]
        rel = os.path.relpath(os.path.join(folder, files[inst]), ROOT) if inst in files else lid
        if level == "error":
            error(f"{rel}（{lid}）", f"行が指すファイル {path} がありません",
                  "読む人やエージェントが、存在しない資料を探すことになります",
                  "正しいパスに直してください（転記で作られる要件・作業一覧のファイルと、書類一覧のテーブルの DDL はまだなくてもよい）")
        else:
            warn(rel, f"{lid} が指す {path} がまだありません")
    for lid, name in gaps.crud(ROOT, folder, cat, w)[1]:
        inst = lid.split("/")[0]
        rel = os.path.relpath(os.path.join(folder, files[inst]), ROOT) if inst in files else lid
        warn(rel, f"{lid}（CRUD）の {name} が DDL にありません。テーブルなら db/schema/{name}.sql を作り、"
                  "列なら DDL に足し、書き間違いなら直してください")


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
        needs = docs[doc]["区分"] == "機能別設計" and cat.role(doc) != "機能の中心"
        if needs and not r["funcs"] and r["作成"] == "書く":
            error(reg_rel, f"{inst} {r['名前']} の「機能」が空です", why, "機能一覧で、この書類を使う機能の行に書いてから list を実行してください")
        for f in r["funcs"]:
            if f not in cat.instances:
                error(reg_rel, f"{inst} の機能 {f} が書類一覧にありません", why, fix_list)
        if r["作成"] == "書く" and inst not in files:
            warn(reg_rel, f"{inst} {r['名前']} はまだファイルがありません（python3 scripts/design/id_design.py scaffold で作れます）")


def removed_ids(folder, base, current):
    """この変更で消えた行ID。base そのものではなく、base と今の分かれ目（merge-base）と比べる。
    分かれた後に base 側で足された行は、この変更が消したのではないので数えない"""
    rel = os.path.relpath(folder, ROOT)
    mb = subprocess.run(["git", "-C", ROOT, "merge-base", "HEAD", base], capture_output=True, text=True)
    if mb.returncode == 0 and mb.stdout.strip():
        base = mb.stdout.strip()
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
        m = catalog.FILE_RE.match(name)
        inst = f"{m.group(1)}-{m.group(3)}"
        old |= {catalog.line_id(inst, under, num) for _, num, _, under in catalog.parse_design(text)[1] if num and under}
    return sorted(old - set(current))


if __name__ == "__main__":
    sys.exit(main())
