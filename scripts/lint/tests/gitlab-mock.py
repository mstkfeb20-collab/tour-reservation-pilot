"""GitLab の API のまね（test-gitlab.sh が使う）。受けた書き込みは、引数のファイルに1行ずつ JSON で残す。

    python3 gitlab-mock.py <ポートを書くファイル> <書き込みの記録>
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

P = "/api/v4/projects/42"
MRS = [
    {"iid": 1, "title": "下書きの MR"},
    {"iid": 2, "title": "CI が落ちた MR"},
    {"iid": 3, "title": "質問のある MR"},
    {"iid": 4, "title": "通った MR"},
    {"iid": 5, "title": "パイプラインのない MR"},
]
ONE = {
    1: {"draft": True, "head_pipeline": {"status": "success"}, "description": ""},
    2: {"draft": False, "head_pipeline": {"status": "failed"}, "description": ""},
    3: {"draft": False, "head_pipeline": {"status": "success"},
        "description": "対象要件: REQ-22001\n\n## レビュアーに判断してほしいこと\n- 取消料の端数は？\n- 返金の期限は？（回答済み）\n"},
    4: {"draft": False, "head_pipeline": {"status": "success"}, "description": "対象要件: REQ-22001\nCloses #7"},
    5: {"draft": False, "head_pipeline": None, "description": ""},
}
DIFFS = {  # MR が触っているファイル（!1 は下書きで設計書を書いている、!3 は設計書のレビュー中）
    1: ["docs/design/S-22-001_予約取消.md"],
    3: ["docs/design/S-22-002_取消一覧.md", "src/main/java/A.java"],
}
ISSUES = [
    {"iid": 7, "title": "REQ-22001 予約取消", "description": "", "assignees": []},
    {"iid": 8, "title": "REQ-22002 取消一覧", "description": "", "assignees": []},
    {"iid": 9, "title": "REQ-22003 取消通知", "description": "", "assignees": [{"username": "sato"}]},
]
NOTES = {  # 2ページに分ける（先頭ページにはレポートのメモがない）
    "1": [{"id": 100, "body": "ふつうのコメント"}],
    "2": [{"id": 101, "body": "<!-- tazuna:pr-report -->\n古いレポート"}],
}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, obj, code=200, headers=None):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.headers.get("PRIVATE-TOKEN") != "t":
            return self.send({"message": "401"}, 401)
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == f"{P}/merge_requests":  # 一覧にも説明・下書きは入る（パイプラインは入らない）
            return self.send([dict(m, description=ONE[m["iid"]]["description"], draft=ONE[m["iid"]]["draft"],
                                   author={"username": f"user{m['iid']}"}) for m in MRS])
        if u.path.startswith(f"{P}/merge_requests/") and u.path.endswith("/notes"):
            page = q.get("page", ["1"])[0]
            return self.send(NOTES[page], headers={"X-Next-Page": "2"} if page == "1" else {})
        if u.path.startswith(f"{P}/merge_requests/") and u.path.endswith("/diffs"):
            n = int(u.path.split("/")[-2])
            return self.send([{"new_path": f, "old_path": f} for f in DIFFS.get(n, [])])
        if u.path.startswith(f"{P}/merge_requests/"):
            n = int(u.path.rsplit("/", 1)[1])
            return self.send(dict(MRS[n - 1], **ONE[n]))
        if u.path == f"{P}/issues":
            if "search" in q:
                return self.send([i for i in ISSUES if q["search"][0] in i["title"]])
            return self.send(ISSUES)
        self.send({"message": "404"}, 404)

    def write(self):
        n = int(self.headers.get("Content-Length") or 0)
        data = json.loads(self.rfile.read(n) or b"{}")
        with open(sys.argv[2], "a", encoding="utf-8") as f:
            f.write(json.dumps({"method": self.command, "path": self.path, "data": data}, ensure_ascii=False) + "\n")
        if self.command == "POST" and self.path == f"{P}/issues":
            return self.send({"iid": 50, "title": data.get("title")}, 201)
        self.send({"id": 1}, 201 if self.command == "POST" else 200)

    do_POST = write
    do_PUT = write


s = HTTPServer(("127.0.0.1", 0), H)
with open(sys.argv[1], "w") as f:
    f.write(str(s.server_address[1]))
s.serve_forever()
