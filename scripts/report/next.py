"""次に何をすればよいかを出す（読むだけで、何も書き換えない）。

    python3 scripts/report/next.py                 # 今の段階と、次にやること（優先順）
    python3 scripts/report/next.py --local          # GitHub・GitLab を見ない（PR・MR・issue・CI を飛ばす）
    python3 scripts/report/next.py --issue REQ-22002  # その要件を実装する issue の下書き

ローカル（設計書・転記・要件・テスト）と GitHub または GitLab（開いている PR・MR・issue・CI）を読み、
止まっているものから順に「誰が・何を・どうやって」を並べる。案内役のスキル（base-navigator）がこれを使って答える。

GitHub か GitLab かは、環境変数 TAZUNA_PLATFORM、git の設定 tazuna.platform（git config tazuna.platform gitlab）、
CI の環境、origin の URL の順で決める。社内の GitLab で URL に gitlab が入らないときは、git の設定で決めておく。
GitLab では gitlab.py が TAZUNA_GITLAB_TOKEN（なければ GITLAB_TOKEN）で読む。
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
import gitlab  # noqa: E402
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


def platform():
    p = os.environ.get("TAZUNA_PLATFORM", "").lower()
    if not p:
        try:
            p = subprocess.run(["git", "-C", ROOT, "config", "--get", "tazuna.platform"],
                               capture_output=True, text=True, timeout=10).stdout.strip().lower()
        except (OSError, subprocess.TimeoutExpired):
            p = ""
    if p in ("github", "gitlab"):
        return p
    if os.environ.get("GITLAB_CI"):
        return "gitlab"
    if os.environ.get("GITHUB_ACTIONS"):
        return "github"
    url = gitlab._origin(ROOT)
    return "gitlab" if "gitlab" in url and "github" not in url else "github"


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
        # 機能一覧が空でも、システムに1つの書類（方式設計書など）は書類一覧に並ぶので、そちらは先に進められる
        todos.append(Todo(80, "社員", "機能一覧を、分かっている範囲で書く",
                          "機能ごとの書類（処理・画面・ジョブ・IF・帳票）は機能一覧から作ります。まだ1行もありません",
                          "docs/design/ID設計.xlsx の「機能一覧」シートに、外部設計で決まっている機能と画面・ジョブ・IF・帳票を書き、"
                          "python3 scripts/design/id_design.py list で書類一覧を作り直す。設計が進んで画面などが増えたら、足して list をやり直す"
                          "（番号は変わらず、新しい書類が末尾に増える）"))

    # 機能一覧と書類一覧のずれ
    sys.path.insert(0, os.path.join(HERE, "..", "design"))
    import id_design  # noqa: E402
    want = {(doc, name) for doc, name, _ in id_design.derive(cat.data, DESIGN)}
    have = {(r["書類ID"], r["名前"]) for r in cat.instances.values() if r["作成"] != "廃止"}
    if want - have or have - want:
        todos.append(Todo(70, "社員", "書類一覧を作り直す",
                          f"機能一覧・もとになる設計書と書類一覧が合っていません（足りない {len(want - have)}・余分 {len(have - want)}）",
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
        # ★ 共通の必須の見出しが空なのに、機能の書類が同じ設計項目を決めている（gaps.py。Lint も警告する）
        import gaps  # noqa: E402
        star = {(i, item): sorted({u for u, _ in users}) for i, item, _, users in gaps.stars(DESIGN, cat)}
        rows = []
        for i in lack:
            _, lines, na = catalog.parse_design(report.read(os.path.join(DESIGN, files[i])))
            written = {u for _, n, t, u in lines if n and not t.startswith("（廃止）")}
            need = [x for x, rec in cat.records.get(cat.instances[i]["書類ID"], {}).items()
                    if rec["記載"] == "必須" and x not in written | na]
            early = [x for x in need if (i, x) in star]
            names = [f"{x} {cat.items[x]['設計項目']}" + (f"（★ {'・'.join(star[(i, x)])} が先に決めている）" if x in early else "")
                     for x in need]
            rows.append((0 if early else 1, i, f"{i} {cat.instances[i]['名前']}: " + "、".join(names)))
        rows.sort()
        first = [r for r in rows if r[0] == 0]
        todos.append(Todo(50, "社員", f"必須の見出しが空の設計書を書く（{len(lack)} 件）",
                          "必須の見出しが埋まるまで、その書類は「完了」になりません。書かないと決めた見出しは「該当なし（理由）」と書く。"
                          + (f"★ の見出しは、機能の書類が先に決めているので、共通の方針・機能に任せる旨・該当なし（理由）のどれかを書く（{len(first)} 件の書類）"
                             if first else ""),
                          "\n".join(r[2] for r in rows)))

    # もとになる設計書の行がまだない書類の種類（例: S-20 のテーブル一覧が空なら、テーブル設計書が1枚もできない）
    import gaps  # noqa: E402
    for t in cat.data.get("書類の種類", []):
        m = id_design.SOURCE_RE.match(id_design.source_of(t))
        if m and (t.get("状態") or "").strip() not in ("廃止", "使わない") and not id_design.source_names(DESIGN, m.group(1), m.group(2)):
            src_doc = cat.docs.get(m.group(1), {}).get("書類名", m.group(1))
            src_item = cat.items.get(m.group(2), {}).get("設計項目", m.group(2))
            todos.append(Todo(55, "社員", f"{src_doc}の「{src_item}」を書く（{t['書類名']}はここから作る）",
                              f"{t['書類名']}は、{m.group(1)} の {m.group(2)} {src_item} の行ごとに1枚できます。まだ1行もありません",
                              f"{m.group(1)} の設計書の「## {m.group(2)} {src_item}」に、1行1つ、行の先頭に名前を書く。"
                              "設計の PR をマージしたら python3 scripts/design/id_design.py list で書類一覧を作り直す"))
    nodll, unlisted = gaps.table_vs_ddl(ROOT, DESIGN)
    unknown = gaps.crud(ROOT, DESIGN, cat)[1]
    if nodll or unlisted or unknown:
        what = ([f"DDL がない {n}（{lid}）" for lid, n in nodll] + [f"テーブル一覧にない DDL {n}" for n in unlisted]
                + [f"CRUD の {n}（{lid}）がテーブル一覧にも DDL の列にもない" for lid, n in unknown])
        todos.append(Todo(45, "社員", f"テーブル一覧・DDL・CRUD をそろえる（{len(what)} 件）",
                          "、".join(what[:6]) + ("…" if len(what) > 6 else ""),
                          "テーブル一覧（S-20 の D-05020）が正。一覧にあるテーブルは db/schema/<テーブル名>.sql を書く（列の説明も）。"
                          "一覧にない DDL は一覧に足すか消す。CRUD の名前がテーブルなら一覧に足し、列なら DDL に足す"))

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


# ---- GitLab ----
# GitLab では、エージェントは手元（VS Code の Copilot）で動く。MR は作業する人が作り、CI の承認待ちはない。

def gitlab_state(facts):
    todos, gfacts = [], {}
    mrs = gitlab.api("projects/:id/merge_requests?state=opened&per_page=100", root=ROOT)
    if mrs is None:
        gfacts["gitlab"] = "見られません（TAZUNA_GITLAB_TOKEN か GITLAB_TOKEN に、read_api のトークンを入れてください）"
        return todos, gfacts
    issues = gitlab.api("projects/:id/issues?state=opened&per_page=100", root=ROOT) or []
    for mr in mrs:
        n, title = mr["iid"], mr["title"]
        one = gitlab.api(f"projects/:id/merge_requests/{n}", root=ROOT) or mr
        pipe = (one.get("head_pipeline") or {}).get("status")
        if one.get("draft") or one.get("work_in_progress"):
            todos.append(Todo(30, "—", f"MR !{n} は作業中（下書き）", title,
                              "作業する人が終えて「Mark as ready」にするのを待つ"))
            continue
        if pipe in ("running", "pending", "created", "waiting_for_resource", "preparing"):
            todos.append(Todo(30, "—", f"MR !{n} の CI が動いている", title, "終わるのを待つ"))
            continue
        if pipe == "manual":
            todos.append(Todo(1, "社員", f"MR !{n} の CI に、手で動かすジョブがある",
                              "手で動かすジョブが終わるまで、パイプラインが完了しません",
                              f"MR !{n} の「Pipelines」で、止まっているジョブの再生ボタンを押す"))
            continue
        if pipe in ("failed", "canceled"):
            todos.append(Todo(2, "社員", f"MR !{n} の CI が失敗している",
                              "Lint かテストが落ちています",
                              f"MR !{n} の「Pipelines」で失敗したジョブを開き、MR の作者が手元の Copilot で直す。"
                              "ハーネス（Lint・hooks）の誤りに見えるなら標準化チームに伝える"))
            continue
        body = one.get("description") or ""
        qs = re.search(r"##[^\n]*判断してほしい[^\n]*\n(.*?)(?=\n## |\Z)", body, re.S)
        open_q = [l for l in (qs.group(1).splitlines() if qs else [])
                  if l.strip().startswith(("- ", "* ", "1")) and not re.search(r"（(回答済み|保留)）", l)]
        if open_q:
            todos.append(Todo(10, "社員", f"MR !{n} の質問に答える（{len(open_q)} 件）",
                              "設計書の穴や、業務で決めることが質問として出ています",
                              "設計書の穴なら設計書を直して転記し、MR の作者に取り込んでもらう。"
                              "業務で決めることなら決めて設計書に書く。決められないものは保留として MR にコメントする"))
        elif pipe == "success":
            todos.append(Todo(20, "社員", f"MR !{n} をレビューしてマージする",
                              "CI が通っています",
                              f"MR !{n} の「tazuna の PR レポート」のメモで、テスト仕様の行と未対応の作業を確かめる。"
                              "問題なければ承認（Approve）→「Squash commits」を付けてマージ"))
        elif pipe is None:
            todos.append(Todo(15, "社員", f"MR !{n} の CI が動いていない",
                              "MR のパイプラインがありません（.gitlab-ci.yml の取り込み漏れ、または Runner がない）",
                              f"MR !{n} の「Pipelines」で「Run pipeline」を押す。動かなければ案件リーダーに伝える"))
    linked = {r for i in issues for r in REQ_RE.findall((i.get("title") or "") + (i.get("description") or ""))}
    for i in issues:
        found = REQ_RE.findall((i.get("title") or "") + (i.get("description") or ""))
        ref = re.compile(rf"#{i['iid']}\b")
        if found and not i.get("assignees") and not any(ref.search(m.get("description") or "") for m in mrs):
            todos.append(Todo(25, "案件リーダー", f"issue #{i['iid']} の担当者を決める",
                              f"要件 {', '.join(sorted(set(found)))} の issue が、まだ誰にも渡っていません",
                              f"issue #{i['iid']} の Assignee に作業する人を入れる。その人が手元の Copilot に issue の本文を渡して作業し、MR を出す"))
    gfacts["prs"], gfacts["issues"] = len(mrs), len(issues)
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
        import gaps
        uses, _ = gaps.crud(ROOT, DESIGN, cat)
        tables = {t for t, lids in uses.items() if any(cat.function_of(l.split("/")[0]) == center for l in lids)}
        mine = [t for t in tasks if center and (cat.function_of(os.path.basename(t)[:8]) == center
                                                or (cat.instances.get(os.path.basename(t)[:8], {}).get("名前") or "").upper() in tables)]
    schema = sorted(os.path.relpath(p, ROOT) for p in __import__("glob").glob(os.path.join(ROOT, "db", "schema", "*.sql")))
    if cat and tables:  # この機能の CRUD に出てくるテーブルだけ
        schema = [p for p in schema if os.path.splitext(os.path.basename(p))[0].upper() in tables]
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
        f"{4 + len(mine)}. 必要に応じて `docs/domain/`、`docs/conventions.md`。`docs/design/` の設計書は背景として読んでよいが、実装とテストの根拠にはしない（下の決まりごと）", "",
        "## 範囲", "", "- 範囲内: （作業一覧のうち、この issue でやるもの）", "- 範囲外: （やらないもの）",
        "- 作業一覧・テスト仕様の行のうち対応しないものは、PR の本文に「未対応: 行ID（理由）」で書く。", "",
        "## 決まりごと", "",
        "- `docs/requirements/`・`docs/design/ID設計.*`・`docs/domain/invariants.md`・`base-*` スキル・共通 Lint・hooks は編集できない。変えたいときは PR の説明に提案を書く。",
        "- 設計書に書かれていないことは推測で埋めず、PR に質問として書く。",
        "- 実装とテストの根拠は、上の要件・作業一覧・DDL と、ID で指された設計書の行だけにする。転記先にない設計書の行を根拠にしたときは、PR の本文に「設計書から: 行ID（理由）」の行で書く。",
        "- PR には実行したコマンドと結果を貼る。", ""])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", help="GitHub・GitLab を見ない")
    ap.add_argument("--issue", help="この要件を実装する issue の下書きを出す（REQ-xxxxx）")
    a = ap.parse_args()
    if a.issue:
        sys.stdout.write(issue_draft(a.issue))
        return
    todos, facts, cat = local_state()
    gfacts = {}
    if not a.local:
        t2, gfacts = (gitlab_state if platform() == "gitlab" else github_state)(facts)
        todos += t2
    else:
        gfacts["unlinked"] = facts.get("untested", [])  # GitHub・GitLab を見ないので、テストのない要件をすべて挙げる
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
        pr = "MR" if platform() == "gitlab" else "PR"
        out.append(f"- 開いている {pr} {gfacts['prs']} 件・issue {gfacts['issues']} 件")
    if "github" in gfacts:
        out.append(f"- GitHub: {gfacts['github']}")
    if "gitlab" in gfacts:
        out.append(f"- GitLab: {gfacts['gitlab']}")
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
