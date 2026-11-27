"""開いている PR（GitLab では MR）と、それが触っている設計書。複数人の進み具合を、リモートの情報だけで全員に同じく見せるため。

- ドラフトの PR が触っている設計書は「執筆中」、ドラフトでない PR は「レビュー中」とする
- 設計書は書き始めたらドラフトの PR を出す決まりにする（手元の変更は他の人から見えないため）
- GitHub は gh、GitLab はトークン（gitlab.py）で読む。読めないときは None を返す（手元の情報だけで決める）

id_design.py progress・report.py daily・next.py が使う。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gitlab  # noqa: E402

INST_RE = re.compile(r"^docs/design/(?:.*/)?(S-\d{2}-\d{3})(?![0-9])")


def platform(root):
    """github か gitlab。TAZUNA_PLATFORM、git の設定 tazuna.platform、CI の環境、origin の URL の順に決める"""
    p = os.environ.get("TAZUNA_PLATFORM", "").lower()
    if not p:
        try:
            p = subprocess.run(["git", "-C", root, "config", "--get", "tazuna.platform"],
                               capture_output=True, text=True, timeout=10).stdout.strip().lower()
        except (OSError, subprocess.TimeoutExpired):
            p = ""
    if p in ("github", "gitlab"):
        return p
    if os.environ.get("GITLAB_CI"):
        return "gitlab"
    if os.environ.get("GITHUB_ACTIONS"):
        return "github"
    url = gitlab._origin(root)
    return "gitlab" if "gitlab" in url and "github" not in url else "github"


def gh(path, root):
    """gh api（{owner}/{repo} は gh が埋める）。使えないときは None"""
    try:
        r = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True, cwd=root, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    text = r.stdout.strip().replace("][", ",")  # --paginate は配列を続けて出す
    try:
        return json.loads(text) if text else []
    except json.JSONDecodeError:
        return None


def open_changes(root):
    """[{ref, draft, author, title, files, sha}]。読めないときは None"""
    if platform(root) == "gitlab":
        mrs = gitlab.api("projects/:id/merge_requests?state=opened&per_page=100", root=root)
        if mrs is None:
            return None
        out = []
        for m in mrs:
            iid = m["iid"]
            diffs = gitlab.api(f"projects/:id/merge_requests/{iid}/diffs?per_page=100", root=root)
            if diffs is None:  # 古い GitLab（15.7 より前）
                diffs = (gitlab.api(f"projects/:id/merge_requests/{iid}/changes", root=root) or {}).get("changes", [])
            out.append({"ref": f"!{iid}", "draft": bool(m.get("draft") or m.get("work_in_progress")),
                        "author": (m.get("author") or {}).get("username", ""), "title": m.get("title", ""),
                        "files": [d.get("new_path") or d.get("old_path") for d in diffs], "sha": m.get("sha", "")})
        return out
    prs = gh("repos/{owner}/{repo}/pulls?state=open&per_page=100", root)
    if prs is None:
        return None
    out = []
    for p in prs:
        files = gh(f"repos/{{owner}}/{{repo}}/pulls/{p['number']}/files?per_page=100", root) or []
        out.append({"ref": f"#{p['number']}", "draft": bool(p.get("draft")),
                    "author": (p.get("user") or {}).get("login", ""), "title": p.get("title", ""),
                    "files": [f.get("filename") for f in files], "sha": (p.get("head") or {}).get("sha", "")})
    return out


def read_file(root, path, sha):
    """PR（MR）の先頭のコミットにあるファイルの中身。読めないときは None"""
    import base64
    import urllib.parse
    q = urllib.parse.quote(path, safe="")
    if platform(root) == "gitlab":
        got = gitlab.api(f"projects/:id/repository/files/{q}?ref={sha}", root=root)
    else:
        got = gh(f"repos/{{owner}}/{{repo}}/contents/{urllib.parse.quote(path)}?ref={sha}", root)
    try:
        return base64.b64decode(got["content"]).decode("utf-8")
    except (TypeError, KeyError, ValueError):
        return None


def by_document(changes):
    """{書類実体ID: [PR]}。設計書のファイル名の書類実体ID で引く（まだ統合先にない新しい設計書も拾う）"""
    out = {}
    for c in changes or []:
        for f in c["files"]:
            m = INST_RE.match(f or "")
            if m and c not in out.setdefault(m.group(1), []):
                out[m.group(1)].append(c)
    return out


def state_of(prs):
    """(状態, PR の表示)。ドラフトでない PR が1つでもあればレビュー中"""
    if not prs:
        return None, ""
    shown = "、".join(f"{p['ref']} {p['author']}" + ("（ドラフト）" if p["draft"] else "") for p in prs)
    return ("執筆中" if all(p["draft"] for p in prs) else "レビュー中"), shown
