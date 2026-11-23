"""自己テスト用: 型の書き出し（docs/design/ID設計.md）に、書類一覧の行だけを差し込んだ書き出しを作る。

    python3 snapshot-for-test.py <出力先> "S-22-001|予約登録|" "S-26-001|予約登録|S-22-001" ...
各行は「書類実体ID|名前|機能[|作成]」。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "design"))
import catalog  # noqa: E402

data = catalog.read_snapshot(os.path.join(ROOT, "docs", "design", catalog.SNAPSHOT))
names = {t["書類ID"]: t["書類名"] for t in data["書類の種類"]}
rows = []
for spec in sys.argv[2:]:
    parts = spec.split("|") + ["", "", "", ""]
    inst, name, funcs, make = parts[0], parts[1], parts[2], parts[3] or "書く"
    rows.append({"書類実体ID": inst, "書類ID": inst[:4], "書類名": names.get(inst[:4], ""), "名前": name, "機能": funcs, "作成": make, "理由": ""})
data["書類一覧"] = rows
catalog.write_snapshot(data, sys.argv[1])
