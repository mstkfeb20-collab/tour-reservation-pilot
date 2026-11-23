"""ID 設計書（docs/design/）の各行を、振り分け先の文書へ転記する。人が実行する。

    python3 scripts/design/transcribe.py            # 転記する
    python3 scripts/design/transcribe.py --check    # 転記した部分を手で直していないかを確かめる（Lint COMMON-008）
    オプション: --design <設計書のフォルダ> --out <転記先のリポジトリのルート>

進め方: ① 設計書を書いて PR でレビュー → ② 機能の資料がそろったらこのツールで転記し、要件とテスト仕様を PR で決める
→ ③ 実装とテスト → ④ Lint と CI を通してマージ。①と②の間に設計と転記先が食い違うのは正常（進捗で「要転記」と出る）。
エラーにするのは、転記した部分を手で書き換えたときだけ。

振り分け先は、見出しの設計項目の3属性（性質・機械検査・業務承認）と、書類の区分で決まる（ID設計.xlsx の振り分け表と同じ）。
行の末尾に {性質:振る舞い 機械検査:実行で可} と書くと、その行だけ属性を上書きできる。
書類がどの機能のものかは、ID設計.xlsx の書類一覧の「機能」で決まる。機能別の書類は、その処理設計書のファイルにまとめる。

転記先（書類実体ごとに目印で囲んだブロック。作り直すたびに丸ごと置き換え、目印の外の手書きには触らない）:
  機能別・テスト・業務承認=要          → docs/requirements/<処理設計書>.md の「## REQ-ddnnn」の完了条件
  テスト仕様書の、テストに振り分ける行 → 同じ要件ファイルの「## テスト仕様」
  共通・テスト・業務承認=要            → docs/domain/candidates/design-<書類>.md（不変条件の候補。社員が承認して invariants へ）
  AIへの条件（主・副とも）             → 機能別: 要件ファイルの「実装するときの条件」 / 共通: docs/conventions.md
  知識                                 → docs/domain/background.md
  設計・Lint・実行検証・hooks・テスト（業務承認=不要）・人のための設計 → docs/tasks/<処理設計書 or 書類>.md（作業一覧）
  機械で守る項目で業務承認=要の根拠    → 機能別: 要件ファイルの「型・Lint で守る決まり」 / 共通: 候補ファイル
"""
import argparse
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog  # noqa: E402

ROOT = os.environ.get("TAZUNA_ROOT") or os.getcwd()
OVER_RE = re.compile(r"\s*\{([^{}]*)\}\s*$")
KEYS = ("性質", "機械検査", "業務承認")
BEGIN = "<!-- tazuna:design {inst} begin src={src}（scripts/design/transcribe.py が作る。手で直さない） -->"
END = "<!-- tazuna:design {inst} end -->"
BLOCK_RE = re.compile(r"<!-- tazuna:design (S-\d{2}-\d{3}) begin src=([0-9a-f]+)[^\n]*-->\n(.*?)\n<!-- tazuna:design \1 end -->", re.S)
TARGET_DIRS = ["docs/requirements", "docs/tasks", "docs/domain/candidates"]
TARGET_FILES = ["docs/conventions.md", "docs/domain/background.md"]
TASK_NAMES = [("設計", "型・API・DB 制約で書けなくする"), ("Lint", "Lint を足す"), ("テスト", "テストを書く（業務承認の要らない振る舞い）"),
              ("実行検証", "動かして測り、PR に結果を添える"), ("hooks", "hooks で操作を止める"), ("人のための設計", "承認されているか確かめる")]


def read_lines(path, inst, cat):
    """[(行ID, 本文, 項番, 属性)]（廃止の行・形の違う行は除く）"""
    _, lines, _ = catalog.parse_design(open(path, encoding="utf-8").read())
    out = []
    for _, num, text, under in lines:
        if under not in cat.items or num is None or text.startswith("（廃止）"):
            continue
        lid = catalog.line_id(inst, under, num)
        x = {k: cat.items[under][k] for k in KEYS}
        o = OVER_RE.search(text)
        if o:
            for part in o.group(1).split():
                k, _, v = part.partition(":")
                if k in KEYS:
                    x[k] = v
            text = text[:o.start()]
        out.append((lid, text, under, x))
    return out


def plan(folder):
    """転記の計画。({相対パス: {書類実体ID: [行]}}, {相対パス: 新規作成時の見出し}, {書類実体ID: 転記元の指紋})"""
    cat = catalog.load(folder)
    if cat is None:
        return {}, {}, {}
    files = catalog.design_files(folder)
    out, headers, srcs = {}, {}, {}

    def put(path, inst, body, header):
        out.setdefault(path, {}).setdefault(inst, []).extend(body)
        headers.setdefault(path, header)

    for inst, name in sorted(files.items()):
        doc = inst[:4]
        if doc not in cat.docs:
            continue
        lines = read_lines(os.path.join(folder, name), inst, cat)
        func = cat.function_of(inst)
        common = cat.layer(doc) == "共通"
        title = name[len(inst) + 1:-3]
        docname = cat.docs[doc]["書類名"]
        label = f"{inst} {docname}：{title}"
        if func:
            fname = cat.instances.get(func, {}).get("名前", "")
            home = files.get(func, catalog.file_name(func, fname))[:-3]
        else:
            home = f"{inst}_{title}"
        home_title = home.split("_", 1)[1]
        srcs[inst] = hashlib.sha1(repr((lines, func, common)).encode()).hexdigest()[:12]

        req, spec, cond, basis, cand, know, tasks = [], [], [], [], [], [], {}
        for lid, text, iid, x in lines:
            main, sub = catalog.destination(x["性質"], x["機械検査"], x["業務承認"])
            entry = f"- {text}（{lid}・{cat.items[iid]['設計項目']}）"
            if main == "テスト" and doc == "S-26":
                spec.append(entry)
            elif main == "テスト" and x["業務承認"] == "要":
                (cand if common else req).append(entry)
            elif main == "AIへの条件":
                cond.append(entry)
            elif main == "知識":
                know.append(entry)
            else:
                tasks.setdefault(main, []).append(f"- [ ] {text}（{lid}・{cat.items[iid]['設計項目']}）")
            if sub == "AIへの条件":
                cond.append(entry)
            if sub == "根拠" and main != "テスト":
                (cand if common else basis).append(entry)

        if not common and (req or cond or basis or spec):
            body = []
            if doc == "S-22" or req:
                suffix = "" if doc == "S-22" else f"（{docname}）"
                body += [f"## REQ-{doc[2:]}{inst[-3:]} {title}{suffix}", "", f"- 背景: ID 設計 {label} で決めた完了条件。", "- 完了条件:"]
                body += [f"  {e}" for e in req]
            elif doc != "S-26" and (cond or basis):
                body += [f"## {title}（{docname}・{inst}）"]
            if spec:
                body += [f"## テスト仕様：{title}（{inst}）", "",
                         "テスト担当は、この観点からテストを作り、各テストに確かめる要件の ID（@Tag）を付ける。", ""] + spec
            if cond:
                body += ["", f"### 実装するときの条件（{inst}）", ""] + cond
            if basis:
                body += ["", f"### 型・Lint で守る決まり（{inst}・業務の承認済み）", ""] + basis
            put(f"docs/requirements/{home}.md", inst, body,
                [f"# {home_title}", "", f"> ID 設計の処理設計書 {home.split('_')[0]} と、書類一覧でこの機能に属する書類から転記した要件。"
                 "設計書を直して転記し直す。目印の中は手で直さない。", ""])
        if common and cond:
            put("docs/conventions.md", inst, [f"## 設計から転記した決まり（{label}）", ""] + cond, ["# 命名・作法", ""])
        if common and cand:
            put(f"docs/domain/candidates/design-{inst}_{title}.md", inst,
                [f"## {label}", "", "社員が各行の判定（承認・却下・保留）を決め、承認したものを invariants.md に「防ぐ層」「担保」付きで移す。", ""]
                + [f"{e}　判定: 未" for e in cand],
                [f"# 不変条件の候補：{title}", "", "> ID 設計から転記した、システム共通の業務ルールの候補。正本ではない。", ""])
        if know:
            put("docs/domain/background.md", inst, [f"## {label}", ""] + know,
                ["# 背景知識", "", "> ID 設計から転記した、判断の材料になる事実。守らせるルールではない。", ""])
        if tasks:
            nested = func is not None and func != inst
            h = "###" if nested else "##"
            body = [f"## {label}", ""] if nested else []
            for k, title_k in TASK_NAMES:
                if k in tasks:
                    body += [f"{h} {title_k}", ""] + tasks[k] + [""]
            put(f"docs/tasks/{home}.md", inst, body[:-1],
                [f"# 作業一覧：{home_title}", "", "> ID 設計から転記した作業。実装の issue から参照する。", ""])
    return out, headers, srcs


def block_text(inst, src, body):
    return "\n".join([BEGIN.format(inst=inst, src=src), *body, END.format(inst=inst)])


def render(current, header, blocks, srcs):
    text = current if current is not None else "\n".join(header) + "\n"
    for inst, body in blocks.items():
        new = block_text(inst, srcs[inst], body)
        pat = re.compile(rf"<!-- tazuna:design {re.escape(inst)} begin.*?<!-- tazuna:design {re.escape(inst)} end -->", re.S)
        text = pat.sub(lambda _: new, text) if pat.search(text) else text.rstrip("\n") + "\n\n" + new + "\n"
    return text


def existing_blocks(out_root):
    """{相対パス: {書類実体ID: (指紋, 本文)}}（転記先にすでにあるブロック）"""
    paths = list(TARGET_FILES)
    for d in TARGET_DIRS:
        full = os.path.join(out_root, d)
        if os.path.isdir(full):
            paths += [f"{d}/{n}" for n in sorted(os.listdir(full)) if n.endswith(".md")]
    found = {}
    for rel in paths:
        full = os.path.join(out_root, rel)
        if os.path.exists(full):
            for m in BLOCK_RE.finditer(open(full, encoding="utf-8").read()):
                found.setdefault(rel, {})[m.group(1)] = (m.group(2), m.group(3))
    return found


def status(folder, out_root):
    """書類実体ごとの転記の状態: 済・要転記・未転記・—（転記するものがない）"""
    want, _, srcs = plan(folder)
    have = existing_blocks(out_root)
    per = {}
    for rel, blocks in want.items():
        for inst in blocks:
            got = have.get(rel, {}).get(inst)
            per.setdefault(inst, []).append("未" if got is None else ("済" if got[0] == srcs[inst] else "古"))
    for rel, blocks in have.items():  # 転記先が変わって、古い場所に残っているブロック
        for inst in blocks:
            if inst in srcs and inst not in want.get(rel, {}):
                per.setdefault(inst, []).append("古")
    out = {}
    for inst in srcs:
        s = per.get(inst)
        out[inst] = "—" if not s else "済" if all(x == "済" for x in s) else "未転記" if all(x == "未" for x in s) else "要転記"
    return out


def hand_edits(folder, out_root):
    """指紋は今の設計と同じ（＝設計は変わっていない）なのに、中身が転記結果と違うブロック"""
    want, _, srcs = plan(folder)
    bad = []
    for rel, blocks in existing_blocks(out_root).items():
        for inst, (src, body) in blocks.items():
            if inst not in srcs or src != srcs[inst]:
                continue  # 設計が変わった（要転記）か、設計書がない
            if inst not in want.get(rel, {}) or body != "\n".join(want[rel][inst]):
                bad.append((rel, inst))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default=os.path.join(ROOT, "docs", "design"))
    ap.add_argument("--out", default=ROOT)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(a.design) or catalog.load(a.design) is None:
        return 0
    if a.check:
        bad = hand_edits(a.design, a.out)
        for rel, inst in bad:
            print(f"ERROR [COMMON-008] {rel}（{inst}）\n  内容: ID 設計から転記した部分が、手で書き換えられています\n"
                  "  理由: 転記した部分の正本は設計書です。手で直すと、次の転記で消え、設計書とも食い違います\n"
                  "  修正: 直したい内容は設計書の方を直し、python3 scripts/design/transcribe.py で転記し直してください\n"
                  "  参照: scripts/design/transcribe.py", file=sys.stderr)
        return 1 if bad else 0
    want, headers, srcs = plan(a.design)
    for rel, blocks in existing_blocks(a.out).items():  # 転記先が変わったブロックを古い場所から外す
        stale = [i for i in blocks if i not in want.get(rel, {})]
        if stale:
            full = os.path.join(a.out, rel)
            text = open(full, encoding="utf-8").read()
            for inst in stale:
                text = re.sub(rf"\n*<!-- tazuna:design {re.escape(inst)} begin.*?<!-- tazuna:design {re.escape(inst)} end -->\n?",
                              "\n", text, flags=re.S)
            with open(full, "w", encoding="utf-8") as fp:
                fp.write(text)
            print("外した:", rel, "、".join(stale))
    for rel, blocks in sorted(want.items()):
        path = os.path.join(a.out, rel)
        current = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        text = render(current, headers[rel], blocks, srcs)
        if text != current:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fp:
                fp.write(text)
            print("転記:", rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
