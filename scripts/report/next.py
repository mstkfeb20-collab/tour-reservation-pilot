"""次に何をすればよいかを出す（読むだけで、何も書き換えない）。

    python3 scripts/report/next.py                 # 今の段階と、次にやること（優先順）
    python3 scripts/report/next.py --local          # GitHub を見ない（PR・issue・CI を飛ばす）
    python3 scripts/report/next.py --issue REQ-22002  # その要件を実装する issue の下書き

ローカル（設計書・転記・要件・テスト）と GitHub（開いている PR・issue・CI）を読み、
止まっているものから順に「誰が・何を・どうやって」を並べる。案内役のスキル（base-navigator）がこれを使って答える。
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "design"))
import catalog  # noqa: E402
import report  # noqa: E402

ROOT = report.ROOT
DESIGN = os.path.join(ROOT, "docs", "design")
REQ_RE = re.compile(r"REQ-\d+")


class Todo:
    def __init__(self, rank, who, what, why, how):
        self.rank, self.who, self.what, self.why, self.how = rank, who, what, why, how


def gh(path):
    """GitHub の REST API（gh が使えなければ None）"""
    try:
        r = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True, cwd=ROOT, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    text = r.stdout.strip().replace("][", ",")  # --paginate は配列を続けて出す
    try:
        return json.loads(text) if text else []
    except json.JSONDecodeError:
        return None


# ---- ローカル ----

def local_state():
    todos, facts = [], {}
    cat = catalog.load(DESIGN) if os.path.isfile(os.path.join(DESIGN, "ID設計.md")) else None
    if cat is None:
        todos.append(Todo(90, "案件リーダー", "ID 設計の書き出し（docs/design/ID設計.md）を作る",
                          "書類一覧と設計書のツールが読む書き出しがありません",
                          "python3 scripts/design/id_design.py export"))
        return todos, facts, None
    if not cat.data.get("機能一覧"):
        todos.append(Todo(80, "社員", "機能一覧を書く",
                          "設計書の一覧は機能一覧から作ります。まだ1行もありません",
                          "docs/design/ID設計.xlsx の「機能一覧」シートに機能・画面・ジョブ・IF・帳票・テーブルを書き、"
                          "python3 scripts/design/id_design.py list で書類一覧を作る"))
        return todos, facts, cat

    # 機能一覧と書類一覧のずれ
    sys.path.insert(0, os.path.join(HERE, "..", "design"))
    import id_design  # noqa: E402
    want = {(doc, name) for doc, name, _ in id_design.derive(cat.data)}
    have = {(r["書類ID"], r["名前"]) for r in cat.instances.values() if r["作成"] != "廃止"}
    if want - have or have - want:
        todos.append(Todo(70, "社員", "書類一覧を作り直す",
                          f"機能一覧と書類一覧が合っていません（足りない {len(want - have)}・余分 {len(have - want)}）",
                          "python3 scripts/design/id_design.py list を実行し、増えた書類の「作成」（書く・書かない）を決める"))

    files = catalog.design_files(DESIGN)
    states = report.doc_states(ROOT)
    nofile = [i for i, r in cat.instances.items() if r["作成"] == "書く" and i not in files]
    if nofile:
        todos.append(Todo(60, "社員", f"設計書のひな形を作る（{len(nofile)} 件）",
                          "書くと決めた書類のファイルがまだありません: " + "、".join(nofile[:6]) + ("…" if len(nofile) > 6 else ""),
                          "python3 scripts/design/id_design.py scaffold"))
    lack = sorted(i for i, (_, st) in states.items() if st in ("未着手", "必須不足") and i in files)
    if lack:
        detail = []
        for i in lack[:8]:
            _, lines, na = catalog.parse_design(report.read(os.path.join(DESIGN, files[i])))
            written = {u for _, n, t, u in lines if n and not t.startswith("（廃止）")}
            need = [x for x, rec in cat.records.get(cat.instances[i]["書類ID"], {}).items()
                    if rec["記載"] == "必須" and x not in written | na]
            detail.append(f"{i} {cat.instances[i]['名前']}（必須の見出し {len(need)} 件が空: "
                          + "、".join(f"{x} {cat.items[x]['設計項目']}" for x in need[:3]) + ("…" if len(need) > 3 else "") + "）")
        todos.append(Todo(50, "社員", f"必須の見出しが空の設計書を書く（{len(lack)} 件）",
                          "必須の見出しが埋まるまで、その書類は「完了」になりません。書かないと決めた見出しは「該当なし（理由）」と書く",
                          "\n".join(detail) + ("\n…" if len(lack) > 8 else "")))

    # 転記
    sys.path.insert(0, os.path.join(HERE, "..", "design"))
    import transcribe  # noqa: E402
    st = transcribe.status(DESIGN, ROOT)
    stale = sorted(i for i, s in st.items() if s in ("要転記", "未転記"))
    if stale:
        todos.append(Todo(40, "社員", f"設計書を転記する（{len(stale)} 件）",
                          "設計書が変わったのに、要件・テスト仕様・作業一覧に反映されていません: " + "、".join(stale[:8]),
                          "設計書の PR がマージされてから python3 scripts/design/transcribe.py を実行し、転記の PR を出す"))
    bad = transcribe.hand_edits(DESIGN, ROOT)
    if bad:
        todos.append(Todo(5, "社員", "転記先が手で直されている",
                          "転記先は設計書から作り直すので、手で直した分は消えます",
                          "設計書の方を直して転記し直す（Lint の COMMON-008 にも出ます）"))

    reqs, _ = report.requirements(ROOT)
    refs = report.test_refs(ROOT)
    facts.update(reqs=reqs, untested=sorted(r for r in reqs if r not in refs),
                 docs=states, done=sum(1 for _, s in states.values() if s == "完了"))
    return todos, facts, cat


# ---- GitHub ----

def github_state(facts):
    todos, gfacts = [], {}
    prs = gh("repos/{owner}/{repo}/pulls?state=open&per_page=100")
    if prs is None:
        gfacts["github"] = "見られません（gh が使えない、またはログインしていない）"
        return todos, gfacts
    issues = [i for i in (gh("repos/{owner}/{repo}/issues?state=open&per_page=100") or []) if "pull_request" not in i]
    for pr in prs:
        n, title = pr["number"], pr["title"]
        copilot = any(a["login"] == "Copilot" for a in pr.get("assignees") or [])
        runs = (gh(f"repos/{{owner}}/{{repo}}/actions/runs?head_sha={pr['head']['sha']}&per_page=50") or {}) \
            if pr.get("head") else {}
        runs = runs.get("workflow_runs", []) if isinstance(runs, dict) else []
        agent = [r for r in runs if re.match(r"(Running Copilot|Addressing comment)", r["name"])]
        working = [r for r in (gh(f"repos/{{owner}}/{{repo}}/actions/runs?branch={pr['head']['ref']}&status=in_progress&per_page=20") or {}).get("workflow_runs", [])
                   if re.match(r"(Running Copilot|Addressing comment)", r["name"])]
        ci = [r for r in runs if r["name"] == "verify"]
        if working:
            todos.append(Todo(30, "—", f"PR #{n} は Copilot が作業中", title, "終わるのを待つ（終わると CI が動き、承認待ちになることがあります）"))
            continue
        if any(r.get("conclusion") == "action_required" for r in ci):
            todos.append(Todo(1, "社員", f"PR #{n} の CI を承認する",
                              "Copilot の PR は、push のたびに人が承認するまで CI が動きません",
                              f"PR #{n} の画面で「Approve and run workflows」を押す"))
            continue
        if any(r.get("conclusion") == "failure" for r in ci):
            todos.append(Todo(2, "社員", f"PR #{n} の CI が失敗している",
                              "Lint かテストが落ちています",
                              f"PR #{n} の「Checks」で失敗したジョブを開く。直すのが PR の作者なら、@copilot で直し方をコメントする。"
                              "ハーネス（Lint・hooks）の誤りに見えるなら標準化チームに伝える"))
            continue
        body = pr.get("body") or ""
        qs = re.search(r"##[^\n]*判断してほしい[^\n]*\n(.*?)(?=\n## |\Z)", body, re.S)
        open_q = [l for l in (qs.group(1).splitlines() if qs else [])
                  if l.strip().startswith(("- ", "* ", "1")) and not re.search(r"（(回答済み|保留)）", l)]
        if open_q:
            todos.append(Todo(10, "社員", f"PR #{n} の質問に答える（{len(open_q)} 件）",
                              "設計書の穴や、業務で決めることが質問として出ています",
                              "設計書の穴なら設計書を直して転記し、PR に「@copilot main を取り込んで…」とコメントする。"
                              "業務で決めることなら決めて設計書に書く。決められないものは保留として PR にコメントする"))
        elif ci and all(r.get("conclusion") == "success" for r in ci[:1]):
            todos.append(Todo(20, "社員", f"PR #{n} をレビューしてマージする",
                              "CI が通っています" + ("（Copilot の PR）" if copilot else ""),
                              f"PR #{n} の「tazuna の PR レポート」のコメントで、テスト仕様の行と未対応の作業を確かめる。"
                              "問題なければ「Ready for review」→ 承認 → Squash and merge"))
    # 要件と issue
    linked = {r for i in issues for r in REQ_RE.findall((i.get("title") or "") + (i.get("body") or ""))}
    for i in issues:
        found = REQ_RE.findall((i.get("title") or "") + (i.get("body") or ""))
        if found and not any(a["login"] == "Copilot" for a in i.get("assignees") or []) \
                and not any(str(i["number"]) in (p.get("body") or "") for p in prs):
            todos.append(Todo(25, "社員", f"issue #{i['number']} を Copilot に割り当てる",
                              f"要件 {', '.join(sorted(set(found)))} の issue が、まだ誰にも渡っていません",
                              f"issue #{i['number']} の Assignees で Copilot を選ぶ"))
    gfacts["prs"], gfacts["issues"] = len(prs), len(issues)
    gfacts["unlinked"] = [r for r in facts.get("untested", []) if r not in linked]
    return todos, gfacts


def issue_draft(req):
    reqs, specs = report.requirements(ROOT)
    if req not in reqs:
        return f"{req} は docs/requirements/ にありません。転記が済んでいるか確かめてください。\n"
    f = reqs[req]
    same = sorted(r for r, x in reqs.items() if x == f)
    tasks = sorted({t for _, _, t in report.tasks(ROOT)})
    cat = catalog.load(DESIGN) if os.path.isfile(os.path.join(DESIGN, "ID設計.md")) else None
    mine = tasks
    if cat:
        m = re.match(r"REQ-(\d{2})(\d{3})$", req)
        center = cat.function_of(f"S-{m.group(1)}-{m.group(2)}") if m else None
        fname = cat.instances.get(center, {}).get("名前") if center else None
        row = next((f for f in cat.data.get("機能一覧", []) if f.get("機能") == fname), {})
        tables = set(catalog.split(row.get("テーブル")))
        mine = [t for t in tasks if center and (cat.function_of(os.path.basename(t)[:8]) == center
                                                or cat.instances.get(os.path.basename(t)[:8], {}).get("名前") in tables)]
    schema = sorted(os.path.relpath(p, ROOT) for p in __import__("glob").glob(os.path.join(ROOT, "db", "schema", "*.sql")))
    return "\n".join([
        f"## やること", "", "（何を作るか・変えるかを1〜2文で）", "",
        "## 完了条件", "",
        f"`{f}` の要件がすべてテストで確かめられ、Lint とテストが通ること。", "",
        *[f"- {r}" for r in same], "",
        "テストは同じファイルの「テスト仕様」の観点から作り、各テストに確かめる要件の `@Tag(\"REQ-xxxxx\")` と、"
        "テスト仕様の行ID `@Tag(\"S-26-xxx/D-xxxxx/n\")` を付ける。既存のテストは消さずに通すこと。", "",
        "PR の本文には次の1行を書く:", "", "```", f"対象要件: {', '.join(same)}", "```", "",
        "## 読むもの", "",
        "1. `AGENTS.md`", f"2. `{f}`（完了条件・テスト仕様・実装するときの条件）",
        *[f"{k}. `{t}`（作業一覧）" for k, t in enumerate(mine, 3)],
        *([f"{3 + len(mine)}. " + "・".join(f"`{s}`" for s in schema) + "（テーブル・列の意味と制約は DDL が正）"] if schema else []),
        f"{4 + len(mine)}. 必要に応じて `docs/design/` の元の設計書、`docs/domain/`、`docs/conventions.md`", "",
        "## 範囲", "", "- 範囲内: （作業一覧のうち、この issue でやるもの）", "- 範囲外: （やらないもの）",
        "- 作業一覧・テスト仕様の行のうち対応しないものは、PR の本文に「未対応: 行ID（理由）」で書く。", "",
        "## 決まりごと", "",
        "- `docs/requirements/`・`docs/design/ID設計.*`・`docs/domain/invariants.md`・`base-*` スキル・共通 Lint・hooks は編集できない。変えたいときは PR の説明に提案を書く。",
        "- 設計書に書かれていないことは推測で埋めず、PR に質問として書く。",
        "- PR には実行したコマンドと結果を貼る。", ""])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", help="GitHub を見ない")
    ap.add_argument("--issue", help="この要件を実装する issue の下書きを出す（REQ-xxxxx）")
    a = ap.parse_args()
    if a.issue:
        sys.stdout.write(issue_draft(a.issue))
        return
    todos, facts, cat = local_state()
    gfacts = {}
    if not a.local:
        t2, gfacts = github_state(facts)
        todos += t2
    else:
        gfacts["unlinked"] = facts.get("untested", [])  # GitHub を見ないので、テストのない要件をすべて挙げる
    for r in gfacts.get("unlinked", []):
        todos.append(Todo(35, "社員", f"{r} を実装する issue を作る",
                          "要件は決まっているのに、テストも開いている issue もありません",
                          f"python3 scripts/report/next.py --issue {r} で下書きを作り、範囲を書いて issue にする"))
    todos.sort(key=lambda t: t.rank)

    docs = facts.get("docs", {})
    if not docs:
        stage = "準備"
    elif any(t.rank <= 30 for t in todos):
        stage = "実装・レビュー"
    elif any(t.rank in (35, 40) for t in todos):
        stage = "転記・issue 化"
    elif any(t.rank <= 80 for t in todos):
        stage = "設計"
    else:
        stage = "止まっているものはありません"
    out = [f"## 今の段階: {stage}", ""]
    if docs:
        out.append(f"- 書類: {len(docs)} 件（完了 {facts.get('done', 0)}）")
        out.append(f"- 要件: {len(facts.get('reqs', {}))} 件（テストなし {len(facts.get('untested', []))}）")
    if "prs" in gfacts:
        out.append(f"- 開いている PR {gfacts['prs']} 件・issue {gfacts['issues']} 件")
    if "github" in gfacts:
        out.append(f"- GitHub: {gfacts['github']}")
    out += ["", "## 次にやること（上から順に）", ""]
    if not todos:
        out.append("止まっているものはありません。")
    for k, t in enumerate(todos, 1):
        out.append(f"{k}. **{t.what}**（{t.who}）")
        out.append(f"   - なぜ: {t.why}")
        for j, line in enumerate(t.how.splitlines()):
            out.append(f"   - {'どうやって: ' if j == 0 else '　'}{line}")
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
