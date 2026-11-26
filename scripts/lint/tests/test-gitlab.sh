#!/usr/bin/env bash
# GitLab で運用するときの道具（scripts/report/gitlab.py と、案内役 next.py の GitLab の読み取り）の自己テスト。
# GitLab の API は、手元で動かすまね（gitlab-mock.py）で代える。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; pass=0; fail=0
w=$(mktemp -d)
python3 "$ROOT/scripts/lint/tests/gitlab-mock.py" "$w/port" "$w/writes" &
mock=$!
trap 'kill $mock 2>/dev/null; rm -rf "$w"' EXIT
for _ in $(seq 50); do [ -s "$w/port" ] && break; sleep 0.1; done
export CI_API_V4_URL="http://127.0.0.1:$(cat "$w/port")/api/v4" CI_PROJECT_ID=42 TAZUNA_GITLAB_TOKEN=t
export no_proxy="127.0.0.1,localhost" NO_PROXY="127.0.0.1,localhost"
unset GITHUB_ACTIONS

check() { if grep -qF -- "$2" <<<"$3"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: $1（「$2」がない）"; echo "$3" | sed 's/^/    /'; fi; }
nocheck() { if grep -qF -- "$2" <<<"$3"; then fail=$((fail + 1)); echo "NG: $1（「$2」がある）"; else pass=$((pass + 1)); fi; }

# --- 案内役 ---
mkdir -p "$w/p/docs/requirements"
printf '## REQ-22001 予約取消\n' > "$w/p/docs/requirements/S-22-001_予約取消.md"
printf '## REQ-22002 取消一覧\n' > "$w/p/docs/requirements/S-22-002_取消一覧.md"
out=$(cd "$w/p" && TAZUNA_ROOT="$w/p" TAZUNA_PLATFORM=gitlab python3 "$ROOT/scripts/report/next.py" 2>&1)
check "MR と issue の数" "開いている MR 5 件・issue 3 件" "$out"
check "下書きの MR は待つ" "MR !1 は作業中（下書き）" "$out"
check "CI が落ちた MR" "MR !2 の CI が失敗している" "$out"
check "答えていない質問だけ数える" "MR !3 の質問に答える（1 件）" "$out"
check "通った MR はレビューしてマージ" "MR !4 をレビューしてマージする" "$out"
check "パイプラインのない MR" "MR !5 の CI が動いていない" "$out"
check "担当者のいない要件の issue" "issue #8 の担当者を決める" "$out"
nocheck "MR が閉じる issue は担当者を求めない" "issue #7 の担当者を決める" "$out"
nocheck "担当者のいる issue は求めない" "issue #9 の担当者を決める" "$out"
nocheck "issue のある要件は issue を作らせない" "REQ-22002 を実装する issue を作る" "$out"
nocheck "GitHub の承認の手順を出さない" "Approve and run workflows" "$out"
# 複数人の進み具合: MR が触っている設計書は、下書きなら執筆中、そうでなければレビュー中
out=$(cd "$ROOT/scripts/report" && TAZUNA_PLATFORM=gitlab python3 -c '
import changes
for i, prs in sorted(changes.by_document(changes.open_changes("'"$w/p"'")).items()):
    print(i, *changes.state_of(prs))' 2>&1)
check "下書きの MR が触る設計書は執筆中" "S-22-001 執筆中 !1 user1（ドラフト）" "$out"
check "下書きでない MR が触る設計書はレビュー中" "S-22-002 レビュー中 !3 user3" "$out"
out=$(cd "$w/p" && TAZUNA_ROOT="$w/p" TAZUNA_PLATFORM=gitlab TAZUNA_GITLAB_TOKEN=x python3 "$ROOT/scripts/report/next.py" 2>&1)
check "読めないときはトークンを案内する" "GitLab: 見られません" "$out"

# --- origin の URL からプロジェクトを決める ---
out=$(cd "$w/p" && git init -q && unset CI_API_V4_URL CI_PROJECT_ID && for u in \
  https://gitlab.example.co.jp/grp/sub/proj.git git@gitlab.example.co.jp:grp/proj.git ssh://git@git.example.co.jp:2222/grp/proj.git; do
  git remote remove origin 2>/dev/null; git remote add origin "$u"
  python3 -c "import sys; sys.path.insert(0, '$ROOT/scripts/report'); import gitlab; print(*gitlab.where('.'))"; done)
check "https の URL" "https://gitlab.example.co.jp/api/v4 grp/sub/proj" "$out"
check "ssh の短い URL" "https://gitlab.example.co.jp/api/v4 grp/proj" "$out"
check "ssh:// とポート" "https://git.example.co.jp/api/v4 grp/proj" "$out"
out=$(cd "$w/p" && git remote set-url origin git@git.example.co.jp:grp/proj.git && unset TAZUNA_PLATFORM && git config tazuna.platform gitlab \
  && TAZUNA_ROOT="$w/p" python3 -c "import sys; sys.path.insert(0, '$ROOT/scripts/report'); import next; print(next.platform())")
check "git の設定で GitLab と決める" "gitlab" "$out"

# --- MR の説明 ---
out=$(CI_MERGE_REQUEST_IID=3 python3 "$ROOT/scripts/report/gitlab.py" mr-body)
check "MR の説明は API の今のものを読む" "取消料の端数は？" "$out"
out=$(CI_MERGE_REQUEST_IID=3 TAZUNA_GITLAB_TOKEN= CI_MERGE_REQUEST_DESCRIPTION="対象要件: なし" python3 "$ROOT/scripts/report/gitlab.py" mr-body)
check "トークンがなければ CI の変数を読む" "対象要件: なし" "$out"

# --- レポートを書く ---
echo "レポートの本文" > "$w/r.md"
CI_MERGE_REQUEST_IID=3 python3 "$ROOT/scripts/report/gitlab.py" mr-note "$w/r.md"
check "前のレポートのメモ（2ページ目）を更新する" '"method": "PUT", "path": "/api/v4/projects/42/merge_requests/3/notes/101"' "$(cat "$w/writes")"
check "目印を付けて書く" '<!-- tazuna:pr-report -->\nレポートの本文' "$(cat "$w/writes")"
: > "$w/writes"
python3 "$ROOT/scripts/report/gitlab.py" issue-note "日次レポート（develop）" "$w/r.md" "説明"
check "issue がなければ作る" '"method": "POST", "path": "/api/v4/projects/42/issues", "data": {"title": "日次レポート（develop）"' "$(cat "$w/writes")"
check "作った issue にメモを足す" '"path": "/api/v4/projects/42/issues/50/notes"' "$(cat "$w/writes")"
: > "$w/writes"
python3 "$ROOT/scripts/report/gitlab.py" issue-note "REQ-22001 予約取消" "$w/r.md"
check "同じ題の issue があればそこに足す" '"path": "/api/v4/projects/42/issues/7/notes"' "$(cat "$w/writes")"
out=$(TAZUNA_GITLAB_TOKEN=x CI_MERGE_REQUEST_IID=3 python3 "$ROOT/scripts/report/gitlab.py" mr-note "$w/r.md" 2>&1); rc=$?
check "書けなくても CI は止めない（理由だけ出す）" "注意: GitLab に書けません" "$out"
[ "$rc" -eq 0 ] && pass=$((pass + 1)) || { fail=$((fail + 1)); echo "NG: 書けないときも終了コードは 0"; }

# --- MR のテンプレートは PR のテンプレートと同じ中身（PR → MR だけ違う）---
want=$(sed -e 's/ PR\([（ ]\)/ MR\1/g; s/PR の本文/MR の説明/g' "$ROOT/.github/pull_request_template.md")
if [ "$want" = "$(cat "$ROOT/.gitlab/merge_request_templates/Default.md")" ]; then pass=$((pass + 1))
else fail=$((fail + 1)); echo "NG: .gitlab/merge_request_templates/Default.md が PR のテンプレートとずれている（PR のテンプレートから作り直す）"; fi

echo "gitlab: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
