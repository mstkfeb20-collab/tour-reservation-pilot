"""開発期間のレポート。git・設計書・要件・作業一覧・テスト・CI の結果を読んで集めるだけで、何も書き換えない。

    python3 scripts/report/report.py pr --base origin/develop --body-file pr.md [--surefire target/surefire-reports] [--lint ok|ng]
    python3 scripts/report/report.py daily --branch develop [--since "24 hours ago"]

pr:    PR 単位。対象要件ごとに、テスト仕様の行がテストで確かめられたか、作業一覧の行のうち未対応にしたもの、
       テストの結果、保護ファイルに触れていないかを出す。CI が PR にコメントする。
daily: ブランチ単位で1日1回。前回から状態が変わった書類、テストありになった要件、入った PR を出す。
       対象のブランチは統合ブランチ（develop など）。main を商用リリース版にする運用では main を対象にしない。

つなぎ目の決まり（docs/requirements/README.md）
  - テストには、確かめたテスト仕様の行 ID を @Tag で付ける（例 @Tag("S-26-002/D-15001/3")）
  - PR の本文には、作業一覧の行のうち対応しなかったものを「未対応: 行ID（理由）」の行で書く
  - 実装・テストの根拠に、転記先にない設計書の行を使ったときは「設計書から: 行ID（理由）」の行で書く。
    レポートは、それが転記先にあるか（見なくてよかった）、ないか（転記の漏れか置き場所の誤り）を分けて出す
"""
import argparse
import fnmatch
import glob
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = os.environ.get("TAZUNA_ROOT") or subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or os.getcwd()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "design"))
import catalog  # noqa: E402

LID = r"S-\d{2}-\d{3}/D-\d{5}/\d+"
LID_RE = re.compile(LID)
REQ_RE = re.compile(r"REQ-\d+")
ENTRY_RE = re.compile(rf"^- (?:\[[ x]\] )?(.*)（({LID})・[^）]*）")
TEST_DIRS = os.environ.get("TAZUNA_TEST_DIRS", "src/test tests").split()


def read(path):
    with open(path, encoding="utf-8") as fp:
        return fp.read()


# ---- 読み取り（どのツリーでも同じように読む。日次では前日のコミットのツリーも読む） ----

def requirements(root):
    """{REQ: ファイル}, {ファイル: [(行ID, 本文)]}（テスト仕様の節の、### より前の行）"""
    reqs, specs = {}, {}
    for path in sorted(glob.glob(os.path.join(root, "docs", "requirements", "*.md"))):
        rel = os.path.relpath(path, root)
        section = None
        for line in read(path).splitlines():
            if line.startswith("## "):
                m = REQ_RE.match(line[3:].strip())
                if m:
                    reqs[m.group(0)] = rel
                section = "spec" if line[3:].startswith("テスト仕様") else None
            elif line.startswith("### "):
                section = None if section == "spec" else section
            elif section == "spec":
                m = ENTRY_RE.match(line)
                if m:
                    specs.setdefault(rel, []).append((m.group(2), m.group(1)))
    return reqs, specs


def tasks(root):
    """[(行ID, 本文, 作業一覧のファイル)]"""
    out = []
    for path in sorted(glob.glob(os.path.join(root, "docs", "tasks", "*.md"))):
        rel = os.path.relpath(path, root)
        for line in read(path).splitlines():
            m = ENTRY_RE.match(line)
            if m and line.startswith("- [ ] "):
                out.append((m.group(2), m.group(1), rel))
    return out


def test_refs(root):
    """{行ID か REQ: {テストのファイル}}"""
    refs = {}
    for d in TEST_DIRS:
        for dirpath, _, names in os.walk(os.path.join(root, d)):
            for n in names:
                path = os.path.join(dirpath, n)
                try:
                    text = read(path)
                except (UnicodeDecodeError, OSError):
                    continue
                rel = os.path.relpath(path, root)
                for key in set(LID_RE.findall(text)) | set(REQ_RE.findall(text)):
                    refs.setdefault(key, set()).add(rel)
    return refs


def doc_states(root):
    """{書類実体ID: (名前, 状態)}。状態はそのツリーの中だけで決める（未着手・必須不足・完了・書かない・廃止）"""
    folder = os.path.join(root, "docs", "design")
    if not os.path.isfile(os.path.join(folder, "ID設計.md")):
        return {}
    cat = catalog.load(folder)
    files = catalog.design_files(folder)
    out = {}
    for inst, r in cat.instances.items():
        if r["作成"] in ("書かない", "廃止"):
            out[inst] = (r["名前"], r["作成"])
            continue
        name = files.get(inst)
        if not name:
            out[inst] = (r["名前"], "未着手")
            continue
        _, lines, na = catalog.parse_design(read(os.path.join(folder, name)))
        written = {u for _, n, t, u in lines if n and not t.startswith("（廃止）")}
        need = {i for i, rec in cat.records.get(r["書類ID"], {}).items() if rec["記載"] == "必須"}
        if not written:
            out[inst] = (r["名前"], "未着手")
        else:
            out[inst] = (r["名前"], "完了" if need <= (written | na) else "必須不足")
    return out


def surefire(folder):
    """(件数, 失敗, エラー, 飛ばした, [失敗したテスト])。結果がなければ None"""
    files = glob.glob(os.path.join(folder, "TEST-*.xml")) if folder else []
    if not files:
        return None
    total = fail = err = skip = 0
    failed = []
    for f in files:
        suite = ET.parse(f).getroot()
        total += int(suite.get("tests", 0))
        fail += int(suite.get("failures", 0))
        err += int(suite.get("errors", 0))
        skip += int(suite.get("skipped", 0))
        for case in suite.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                failed.append(f"{case.get('classname')}.{case.get('name')}")
    return total, fail, err, skip, failed


def git(*args, cwd=None):
    return subprocess.run(["git", "-C", cwd or ROOT, *args], capture_output=True, text=True)


def protected_patterns(root):
    path = os.path.join(root, ".github", "hooks", "protected-paths.txt")
    if not os.path.isfile(path):
        return []
    return [p.strip() for p in read(path).splitlines() if p.strip() and not p.startswith("#")]


# ---- PR 単位 ----

def body_lines(body, label):
    """本文の「ラベル: …」の行（引用・コードの中は除く）"""
    out, fence = [], False
    for line in (body or "").splitlines():
        if line.strip().startswith("```"):
            fence = not fence
            continue
        if not fence and re.match(rf"^[ \t]*{label}[:：]", line):
            out.append(line.split(":", 1)[-1].split("：", 1)[-1].strip())
    return out


def pr_report(base, body, surefire_dir=None, lint=None):
    reqs, specs = requirements(ROOT)
    refs = test_refs(ROOT)
    targets = [r for line in body_lines(body, "対象要件") for r in REQ_RE.findall(line)]
    skipped = {}
    for line in body_lines(body, "未対応"):
        for lid in LID_RE.findall(line) + re.findall(r"S-\d{2}-\d{3}/D-\d{5}(?![/\d])", line):
            reason = re.sub(rf"^.*?{re.escape(lid)}", "", line).strip(" 　（）()")
            skipped[lid] = reason or "（理由なし）"
    out = ["## tazuna の PR レポート", ""]
    if not targets:
        out += ["対象要件: なし（要件を実装しない PR）", ""]

    # 対象要件ごとのテスト仕様の行
    files = sorted({reqs[t] for t in targets if t in reqs})
    if targets:
        out += ["### 対象要件とテスト", "", "| 要件 | テスト（要件 ID を付けたもの） |", "| --- | --- |"]
        for t in targets:
            n = len(refs.get(t, ()))
            out.append(f"| {t} | {'定義なし' if t not in reqs else (f'{n} ファイル' if n else '**なし**')} |")
        out.append("")
    for f in files:
        rows = specs.get(f, [])
        if not rows:
            continue
        tested = [lid for lid, _ in rows if lid in refs]
        listed = [lid for lid, _ in rows if lid not in refs and lid in skipped]
        missing = [(lid, t) for lid, t in rows if lid not in refs and lid not in skipped]
        out += [f"### テスト仕様の行（{f}）", "",
                f"テストで確かめた {len(tested)} ・ 未対応と書いた {len(listed)} ・ **どちらでもない {len(missing)}** （全 {len(rows)} 行）", ""]
        for lid, t in missing:
            out.append(f"- [ ] {lid} {t}")
        for lid in listed:
            out.append(f"- 未対応 {lid}: {skipped[lid]}")
        out.append("")

    # 作業一覧（対象要件の機能に属する書類の作業）
    folder = os.path.join(ROOT, "docs", "design")
    if targets and os.path.isfile(os.path.join(folder, "ID設計.md")):
        cat = catalog.load(folder)
        funcs = set()
        for t in targets:
            m = re.match(r"REQ-(\d{2})(\d{3})$", t)
            inst = f"S-{m.group(1)}-{m.group(2)}" if m else None
            if inst and inst in cat.instances and cat.function_of(inst):
                funcs.add(cat.function_of(inst))
        mine = [(lid, t, f) for lid, t, f in tasks(ROOT) if cat.function_of(lid.split("/")[0]) in funcs]
        if mine:
            listed = [lid for lid, _, _ in mine if lid in skipped]
            out += ["### 作業一覧", "",
                    f"この機能の作業 {len(mine)} 行のうち、未対応と書いたもの {len(listed)} 行（ほかは対応したものとして扱う）", ""]
            out += [f"- 未対応 {lid}: {skipped[lid]}" for lid in listed]
            out.append("")
        # ★ この機能の書類が先に決めている、共通の書類の空の必須見出し
        import gaps
        mystars = [(i, item, name) for i, item, name, users in gaps.stars(folder, cat)
                   if any(cat.function_of(u) in funcs for u, _ in users)]
        if mystars:
            keys = [f"{i}/{item}" for i, item, _ in mystars]
            out += ["### ★ この機能が先に決めている共通の見出し", "",
                    f"共通の書類の必須の見出しが空のまま、この機能の書類が先に決めているもの {len(mystars)} 件のうち、"
                    f"**扱いが書かれていない {sum(1 for k in keys if k not in skipped)} 件**"
                    "（設計書に共通の方針・機能に任せる旨・該当なし（理由）を書けば消える。今は直さないなら本文に「未対応: S-xx-nnn/D-xxxxx（理由）」）", ""]
            for (i, item, name), k in zip(mystars, keys):
                out.append(f"- 未対応 {k} {name}: {skipped[k]}" if k in skipped else f"- [ ] {k} {name}")
            out.append("")
        unknown = [lid for lid in skipped if lid not in {l for l, _, _ in mine} and lid not in {l for f in files for l, _ in specs.get(f, [])}
                   and lid not in {f"{i}/{item}" for i, item, _ in mystars}]
        if unknown:
            out += ["未対応に書いたが、この機能の作業・テスト仕様にない行: " + ", ".join(unknown), ""]

    # 設計書から直接読んだ行（根拠は転記先が原則。ここに出るものは、転記か設計書を直す候補）
    direct = {}
    for line in body_lines(body, "設計書から"):
        for lid in LID_RE.findall(line):
            direct[lid] = re.sub(rf"^.*?{re.escape(lid)}", "", line).strip(" 　（）()") or "（理由なし）"
    if direct:
        folder = os.path.join(ROOT, "docs", "design")
        import gaps
        live = {lid for _, _, rows in gaps.written(folder).values() for lid, _, _ in rows} \
            if os.path.isfile(os.path.join(folder, "ID設計.md")) else set()
        moved = "\n".join(read(p) for p in glob.glob(os.path.join(ROOT, "docs", "requirements", "*.md"))
                          + glob.glob(os.path.join(ROOT, "docs", "tasks", "*.md")))
        kinds = {"ない": [], "ある": [], "なし": []}
        for lid, why in direct.items():
            k = "なし" if lid not in live else ("ある" if lid in moved else "ない")
            kinds[k].append(f"- {lid}: {why}")
        out += ["### 設計書から直接読んだ行", "",
                f"実装・テストの根拠にした設計書の行 {len(direct)} 件（根拠は転記先が原則）", ""]
        if kinds["ない"]:
            out += ["**転記先にない**（転記の漏れか、設計書の置き場所の誤り。転記ツールか設計書を直す候補）", ""] + kinds["ない"] + [""]
        if kinds["ある"]:
            out += ["転記先にある（設計書を見なくてよかった）", ""] + kinds["ある"] + [""]
        if kinds["なし"]:
            out += ["**設計書にない行ID**（書き間違いか、消えた行）", ""] + kinds["なし"] + [""]

    # テストの結果・Lint
    res = surefire(surefire_dir)
    out += ["### テストと Lint", ""]
    if res:
        total, fail, err, skip, failed = res
        out.append(f"- テスト: {total} 件（失敗 {fail}・エラー {err}・飛ばした {skip}）")
        out += [f"  - 失敗: {n}" for n in failed[:20]]
    else:
        out.append("- テスト: 結果なし")
    if lint:
        out.append(f"- Lint: {'通過' if lint == 'ok' else '**失敗**'}")

    # 変更したファイルと保護ファイル
    changed = [p for p in git("diff", "--name-only", f"{base}...HEAD").stdout.splitlines() if p]
    pats = protected_patterns(ROOT)
    touched = [p for p in changed if any(fnmatch.fnmatchcase(p, pat) for pat in pats)]
    out.append(f"- 変更したファイル: {len(changed)}")
    out.append(f"- 保護ファイルの変更: {'なし' if not touched else '**' + ', '.join(touched) + '**'}")
    return "\n".join(out) + "\n"


# ---- 日次 ----

def daily_report(branch, since):
    head = git("rev-parse", "-q", "--verify", branch + "^{commit}").stdout.strip()
    if not head:
        return f"## 日次レポート（{branch}）\n\nブランチ {branch} がありません。\n"
    old = git("rev-list", "-1", f"--before={since}", branch).stdout.strip()
    out = [f"## 日次レポート（{branch}）", "", f"- 対象: {head[:7]}（前回: {old[:7] if old else 'なし'}、{since} 以降）"]
    commits = git("log", "--oneline", "--no-merges", f"{old}..{head}" if old else head, "-n", "50").stdout.splitlines()
    out += [f"- コミット: {len(commits)} 件", ""]

    now_docs = doc_states(ROOT)
    now_reqs, _ = requirements(ROOT)
    now_refs = test_refs(ROOT)
    old_docs, old_reqs, old_refs = {}, {}, {}
    tmp = None
    if old and old != head:
        tmp = os.path.join(ROOT, ".git", "tazuna-report-old")
        git("worktree", "remove", "--force", tmp)
        if git("worktree", "add", "--detach", tmp, old).returncode == 0:
            old_docs, (old_reqs, _), old_refs = doc_states(tmp), requirements(tmp), test_refs(tmp)
    try:
        changes = [(i, now_docs[i][0], old_docs.get(i, ("", "（なし）"))[1], now_docs[i][1])
                   for i in sorted(now_docs) if old_docs.get(i, ("", "（なし）"))[1] != now_docs[i][1]]
        out += ["### 状態が変わった書類", ""]
        out += [f"- {i} {n}: {a} → {b}" for i, n, a, b in changes] or ["- なし"]
        new_reqs = sorted(set(now_reqs) - set(old_reqs))
        tested = sorted(r for r in now_reqs if r in now_refs and r not in old_refs)
        out += ["", "### 要件", "", f"- 新しく決まった要件: {', '.join(new_reqs) or 'なし'}",
                f"- テストありになった要件: {', '.join(tested) or 'なし'}",
                f"- テストのまだない要件: {', '.join(sorted(r for r in now_reqs if r not in now_refs)) or 'なし'}"]
        counts = {}
        for _, st in now_docs.values():
            counts[st] = counts.get(st, 0) + 1
        out += ["", "### 書類の状態（全体）", "", "- " + "・".join(f"{k} {v}" for k, v in sorted(counts.items())) if counts else "- 書類一覧なし"]
        out += ["", "### コミット", ""] + [f"- {c}" for c in commits[:30]]
    finally:
        if tmp:
            git("worktree", "remove", "--force", tmp)
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pr")
    p.add_argument("--base", required=True)
    p.add_argument("--body-file")
    p.add_argument("--surefire")
    p.add_argument("--lint", choices=["ok", "ng"])
    p = sub.add_parser("daily")
    p.add_argument("--branch", required=True)
    p.add_argument("--since", default="24 hours ago")
    a = ap.parse_args()
    if a.cmd == "pr":
        body = read(a.body_file) if a.body_file else os.environ.get("TAZUNA_PR_BODY", "")
        sys.stdout.write(pr_report(a.base, body, a.surefire, a.lint))
    else:
        sys.stdout.write(daily_report(a.branch, a.since))


if __name__ == "__main__":
    main()
