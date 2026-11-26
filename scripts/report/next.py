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
import changes  # noqa: E402
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
    return changes.platform(ROOT)


# ---- 立ち上げ（テンプレートから作った直後） ----

def repo_name():
    url = gitlab._origin(ROOT).rstrip("/")
    name = re.split(r"[/:]", url)[-1] if url else ""
    return name[:-4] if name.endswith(".git") else name


def setup_state():
    """README の「新しいプロジェクトを始める」のうち、ファイルを見て分かるものが済んでいるか。tazuna 本体では何も出さない"""
    todos = []
    if os.path.isdir(os.path.join(ROOT, "_tazuna")):
        if repo_name().lower() in ("", "tazuna"):
            return todos  # tazuna 本体
        todos.append(Todo(-4, "案件リーダー", "tazuna 本体専用のフォルダ _tazuna/ を消す",
                          "このフォルダがあると、hooks が型のファイル（base スキル・共通 Lint・hooks・CI）の編集を許します",
                          "git rm -r _tazuna してコミットする（README「新しいプロジェクトを始める」の 2）"))

    def has(rel, text):
        try:
            return text in report.read(os.path.join(ROOT, rel))
        except OSError:
            return False
    if has(".github/CODEOWNERS", "@your-org") or has(".gitlab/CODEOWNERS", "@your-org"):
        todos.append(Todo(-3, "案件リーダー", "CODEOWNERS の承認者を実際のチームにする",
                          "@your-org のままでは、設計書・要件・型の変更を誰が承認するかが決まりません",
                          "CODEOWNERS の @your-org/... を実際のチーム（GitLab ならグループ）に置き換える（README の 3）"))
    if has("AGENTS.md", "[プロジェクト名]"):
        todos.append(Todo(-2, "案件リーダー", "AGENTS.md をこの案件のものにする",
                          "プロジェクト名とコマンドが見本のままです。エージェントが毎回読むファイルです",
                          "AGENTS.md の [ ] の部分を書き換える（60行以内）。pom.xml・src/ のパッケージ名も合わせる（README の 3）"))
    if has("docs/requirements/reservation.md", "見本"):
        todos.append(Todo(-1, "社員", "見本の要件・不変条件・用語を消す",
                          "ツアー予約の見本（docs/requirements/reservation.md など）が残っていると、エージェントが案件の要件と取り違えます",
                          "docs/requirements/reservation.md と docs/domain/ の見本の行を消す。要件は ID 設計から転記して作る（README の 3）"))
    return todos


# ---- PR・MR の質問（人の答えはコメントで受ける。本文は Copilot が書き換えるので人は編集しない） ----

QSEC_RE = re.compile(r"##[^\n]*判断してほしい[^\n]*\n(.*?)(?=\n## |\Z)", re.S)
ANSWER_RE = re.compile(r"^[ \t>]*(回答|保留)[:：][ \t]*([0-9０-９][0-9０-９,，、 \t]*)", re.M)


def open_questions(body, comments):
    """[(番号, 質問)]。番号は「判断してほしいこと」の節の質問の行の上からの順。
    人のコメントの「回答: 1, 3」「保留: 2」の行と、本文の（回答済み）（保留）で答えたものとする"""
    m = QSEC_RE.search(body or "")
    lines = [l.strip() for l in (m.group(1).splitlines() if m else [])
             if l.strip().startswith(("- ", "* ")) or re.match(r"\s*[0-9]+[.)．]", l)]
    done = set()
    for c in comments:
        for _, nums in ANSWER_RE.findall(c):
            nums = nums.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
            done |= {int(x) for x in re.findall(r"\d+", nums)}
    return [(k, re.sub(r"^(?:[-*]|[0-9]+[.)．])\s*", "", l)) for k, l in enumerate(lines, 1)
            if k not in done and not re.search(r"（(回答済み|保留)）", l)]


def question_todo(kind, n, qs, how_more):
    shown = "／".join(f"{k}. {q}" for k, q in qs[:3]) + ("…" if len(qs) > 3 else "")
    return Todo(10, "社員", f"{kind} の質問に答える（{len(qs)} 件）",
                "設計書の穴や、業務で決めることが質問として出ています: " + shown,
                f"答えを決めたら、{kind} のコメントに「回答: 1」（いくつかなら「回答: 1, 3」、今は決められないものは「保留: 2」）の行を書く。"
                "本文は編集しない（Copilot が本文を書き換えなくなる）\n" + how_more)


# ---- 不具合（結合・総合テストなど、このリポジトリの外で見つかったものの戻り口） ----

BUG_CAUSES = ("設計", "転記", "実装", "ハーネス")


def is_bug(issue):
    labels = [l if isinstance(l, str) else l.get("name", "") for l in issue.get("labels") or []]
    return "不具合" in labels or (issue.get("title") or "").startswith("【不具合】")


def bug_todos(issue, num, body, assigned, pr):
    """原因区分ごとに、誰が何をするか"""
    m = re.search(r"^[ \t]*原因区分[:：][ \t]*(\S*)", body or "", re.M)
    cause = next((c for c in BUG_CAUSES if m and m.group(1).startswith(c)), None)
    title = issue.get("title") or ""
    if cause is None:
        return [Todo(7, "社員", f"不具合 #{num} の原因を切り分ける", title,
                     f"案内役に「不具合 #{num} を切り分けて」と頼むと、根拠の行 ID から設計書・転記先・テストを読み、"
                     "どこで食い違ったかの候補を出す。決めたら issue の「原因区分:」を 設計・転記・実装・ハーネス のどれかにする")]
    if cause == "設計":
        return [Todo(8, "社員", f"不具合 #{num} の設計書を直す", title,
                     "設計書を直して PR でレビューし、転記する。転記で変わった要件を実装する issue を作り、この不具合の番号を書く")]
    if cause == "転記":
        return [Todo(8, "標準化チーム", f"不具合 #{num} の転記ツールを直す", title,
                     "設計書の行が転記先にどう入るべきだったかを issue に書いて tazuna に修正を依頼する。直るまでは、PR に「設計書から: 行ID（理由）」で書いて進める")]
    if cause == "ハーネス":
        return [Todo(8, "案件リーダー", f"不具合 #{num} をハーネスの不具合として渡す", title,
                     "harness/rule-log.md に1行書き、再現の手順をまとめて標準化チームに渡す（案件の中では直さない）")]
    if assigned:
        return []  # 実装の誤りで、もう誰かが作業している
    return [Todo(9, "社員", f"不具合 #{num} の修正を割り当てる", title,
                 f"issue に直す要件（REQ-xxxxx）と、確かめるテスト仕様の行 ID を書いてから、{pr}")]


# ---- ローカル ----

def local_state(busy=None):
    """busy: 開いている PR で書いている最中の書類 {書類実体ID: 表示}（--local では空）"""
    busy = busy or {}
    todos, facts = [], {}
    cat = catalog.load(DESIGN) if os.path.isfile(os.path.join(DESIGN, "ID設計.md")) else None
    if cat is None:
        todos.append(Todo(90, "案件リーダー", "ID 設計の書き出し（docs/design/ID設計.md）を作る",
                          "書類一覧と設計書のツールが読む書き出しがありません",
                          "python3 scripts/design/id_design.py export"))
        return todos, facts, None
    if not cat.data.get("機能一覧"):
        # 機能一覧が空でも、システムに1つの書類（方式設計書など）は書類一覧に並ぶので、そちらは先に進められる
        todos.append(Todo(51, "社員", "機能一覧を、分かっている範囲で書く",
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
        todos.append(Todo(52, "社員", "書類一覧を作り直す",
                          f"機能一覧・もとになる設計書と書類一覧が合っていません（足りない {len(want - have)}・余分 {len(have - want)}）",
                          "python3 scripts/design/id_design.py list を実行し、増えた書類の「作成」（書く・書かない）を決める"))

    files = catalog.design_files(DESIGN)
    states = report.doc_states(ROOT)
    nofile = [i for i, r in cat.instances.items() if r["作成"] == "書く" and i not in files]
    if nofile:
        todos.append(Todo(53, "社員", f"設計書のひな形を作る（{len(nofile)} 件）",
                          "書くと決めた書類のファイルがまだありません: " + "、".join(nofile[:6]) + ("…" if len(nofile) > 6 else ""),
                          "python3 scripts/design/id_design.py scaffold"))
    lack = sorted(i for i, (_, st) in states.items() if st in ("未着手", "必須不足") and i in files and i not in busy)
    if busy:
        facts["busy"] = busy
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
        todos.append(Todo(55, "社員", f"必須の見出しが空の設計書を書く（{len(lack)} 件）",
                          "必須の見出しが埋まるまで、その書類は「完了」になりません。書かないと決めた見出しは「該当なし（理由）」と書く。"
                          "書き始めたら、まずドラフトの PR を出す（誰が書いているかが全員に見え、二重に書かずに済む）。"
                          + (f"★ の見出しは、機能の書類が先に決めているので、共通の方針・機能に任せる旨・該当なし（理由）のどれかを書く（{len(first)} 件の書類）"
                             if first else ""),
                          "\n".join(r[2] for r in rows)))

    # もとになる設計書の行がまだない書類の種類（例: S-20 のテーブル一覧が空なら、テーブル設計書が1枚もできない）
    import gaps  # noqa: E402
    for t in cat.data.get("書類の種類", []):
        m = id_design.SOURCE_RE.match(id_design.source_of(t))
        # もとになる書類のファイルがまだなければ案内しない（先に「ひな形を作る」が出る。ないファイルに書けとは言わない）
        src_files = [i for i, r in cat.instances.items() if r["書類ID"] == (m.group(1) if m else None) and i in files]
        if m and src_files and (t.get("状態") or "").strip() not in ("廃止", "使わない") \
                and not id_design.source_names(DESIGN, m.group(1), m.group(2)):
            src_doc = cat.docs.get(m.group(1), {}).get("書類名", m.group(1))
            src_item = cat.items.get(m.group(2), {}).get("設計項目", m.group(2))
            todos.append(Todo(54, "社員", f"{src_doc}の「{src_item}」を書く（{t['書類名']}はここから作る）",
                              f"{t['書類名']}は、{m.group(1)} の {m.group(2)} {src_item} の行ごとに1枚できます。まだ1行もありません",
                              f"{src_files[0]} {files[src_files[0]]} の「## {m.group(2)} {src_item}」に、1行1つ、行の先頭に名前を書く。"
                              "設計の PR をマージしたら python3 scripts/design/id_design.py list で書類一覧を作り直す"))
    nodll, unlisted = gaps.table_vs_ddl(ROOT, DESIGN)
    unknown = gaps.crud(ROOT, DESIGN, cat)[1]
    if nodll or unlisted or unknown:
        what = ([f"DDL がない {n}（{lid}）" for lid, n in nodll] + [f"テーブル一覧にない DDL {n}" for n in unlisted]
                + [f"CRUD の {n}（{lid}）がテーブル一覧にも DDL の列にもない" for lid, n in unknown])
        todos.append(Todo(56, "社員", f"テーブル一覧・DDL・CRUD をそろえる（{len(what)} 件）",
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
    _, specs = report.requirements(ROOT)
    facts["handoff"] = [(f, lid, text) for f, rows in specs.items() for lid, text in rows if lid not in refs]
    facts["specs"] = sum(len(rows) for rows in specs.values())
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
        comments = [c.get("body") or "" for c in (gh(f"repos/{{owner}}/{{repo}}/issues/{n}/comments?per_page=100") or [])
                    if (c.get("user") or {}).get("type") != "Bot" and (c.get("user") or {}).get("login") != "Copilot"]
        open_q = open_questions(body, comments)
        if open_q:
            todos.append(question_todo(f"PR #{n}", n, open_q,
                                       "設計書の穴なら設計書を直して転記し、PR に「@copilot main を取り込んで…」とコメントする。"
                                       "業務で決めることなら決めて設計書に書く"))
        elif ci and all(r.get("conclusion") == "success" for r in ci[:1]):
            todos.append(Todo(20, "社員", f"PR #{n} をレビューしてマージする",
                              "CI が通っています" + ("（Copilot の PR）" if copilot else ""),
                              f"PR #{n} の「tazuna の PR レポート」のコメントで、テスト仕様の行と未対応の作業を確かめる。"
                              "問題なければ「Ready for review」→ 承認 → Squash and merge"))
    # 要件と issue
    linked = {r for i in issues for r in REQ_RE.findall((i.get("title") or "") + (i.get("body") or ""))}
    for i in issues:
        if is_bug(i):
            todos += bug_todos(i, i["number"], i.get("body"), bool(i.get("assignees")),
                               f"issue #{i['number']} の Assignees で Copilot を選ぶ")
            continue
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
        notes = [x.get("body") or "" for x in (gitlab.api(f"projects/:id/merge_requests/{n}/notes?per_page=100", root=ROOT) or [])
                 if not x.get("system")]
        open_q = open_questions(body, notes)
        if open_q:
            todos.append(question_todo(f"MR !{n}", n, open_q,
                                       "設計書の穴なら設計書を直して転記し、MR の作者に取り込んでもらう。"
                                       "業務で決めることなら決めて設計書に書く"))
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
        if is_bug(i):
            todos += bug_todos(i, i["iid"], i.get("description"), bool(i.get("assignees")),
                               f"issue #{i['iid']} の Assignee に作業する人を入れる")
            continue
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
    busy = {}
    if not a.local:
        for inst, prs in changes.by_document(changes.open_changes(ROOT)).items():
            st, shown = changes.state_of(prs)
            busy[inst] = f"{st}（{shown}）"
    todos, facts, cat = local_state(busy)
    todos = setup_state() + todos
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
    handoff = False
    if any(t.rank < 0 for t in todos):
        stage = "立ち上げ"
    elif not docs:
        stage = "準備"
    elif any(t.rank <= 30 for t in todos):
        stage = "実装・レビュー"
    elif any(t.rank in (35, 40) for t in todos):
        stage = "転記・issue 化"
    elif any(t.rank <= 80 for t in todos):
        stage = "設計"
    elif facts.get("reqs"):
        stage, handoff = "単体テストまで完了（結合テストへ引き渡す）", True
    else:
        stage = "止まっているものはありません"
    out = [f"## 今の段階: {stage}", ""]
    if docs:
        out.append(f"- 書類: {len(docs)} 件（完了 {facts.get('done', 0)}）")
        if facts.get("busy"):
            out.append("- 開いている PR で書いている・レビュー中の書類: "
                       + "、".join(f"{i} {v}" for i, v in sorted(facts["busy"].items())))
        out.append(f"- 要件: {len(facts.get('reqs', {}))} 件（テストなし {len(facts.get('untested', []))}）")
    if "prs" in gfacts:
        pr = "MR" if platform() == "gitlab" else "PR"
        out.append(f"- 開いている {pr} {gfacts['prs']} 件・issue {gfacts['issues']} 件")
    if "github" in gfacts:
        out.append(f"- GitHub: {gfacts['github']}")
    if "gitlab" in gfacts:
        out.append(f"- GitLab: {gfacts['gitlab']}")
    out += ["", "## 次にやること（上から順に）", ""]
    if handoff:
        rows = facts.get("handoff", [])
        out += ["このリポジトリ（tazuna）の範囲は単体テストまでで、すべての要件にテストがあります。"
                "結合・総合テストは、作る人と試験する人を分けるため、ED・SP から試験チームが別に起こします。次を渡してください。", "",
                f"- 要件 {len(facts['reqs'])} 件。テスト仕様 {facts.get('specs', 0)} 行のうち、単体テストで確かめた {facts.get('specs', 0) - len(rows)} 行",
                "- 単体テストで確かめていないテスト仕様の行" + ("（PR に「未対応」と書いた行。理由はその PR の本文）:" if rows else ": なし")]
        out += [f"  - {lid} {text}（{f}）" for f, lid, text in rows]
        out += ["- 結合・総合テストで見つかった不具合は、このリポジトリの issue に「不具合」のテンプレートで書いてもらう。"
                "ここへ戻る入口で、原因（設計・転記・実装・ハーネス）を切り分けて直す", ""]
    elif not todos:
        out.append("止まっているものはありません。")
    for k, t in enumerate(todos, 1):
        out.append(f"{k}. **{t.what}**（{t.who}）")
        out.append(f"   - なぜ: {t.why}")
        for j, line in enumerate(t.how.splitlines()):
            out.append(f"   - {'どうやって: ' if j == 0 else '　'}{line}")
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
