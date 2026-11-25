#!/usr/bin/env bash
# design_docs.py（COMMON-007）の自己テスト。壊した設計書を1つずつ置き、期待どおり止まるかを確かめる。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"
PY="$ROOT/scripts/lint/common/design_docs.py"
pass=0; fail=0

good='# S-21-002 画面設計書：予約入力

## D-02002 画面項目定義

- [1] 大人人数: プルダウン
- [2] 備考: テキストエリア、最大80文字
'

SNAP="$ROOT/scripts/lint/tests/snapshot-for-test.py"

# case <名前> <期待（ok|ng）> <ファイル名> <本文> [期待するメッセージの一部] [書類一覧の行（"書類実体ID|名前|機能" を ; 区切り。
#   省略時はファイル名から作る。"none" なら書き出しを置かない）]
case_() {
  local name="$1" expect="$2" file="$3" body="$4" needle="${5:-}" reg="${6:-}"
  local dir; dir=$(mktemp -d)
  printf '%s' "$body" > "$dir/$file"
  if [ -z "$reg" ]; then
    local stem="${file%.md}" fn=""
    case "$stem" in S-21-*|S-23-*|S-24-*|S-25-*|S-26-*) fn="S-22-001" ;; esac
    reg="${stem%%_*}|${stem#*_}|$fn;S-22-001|予約登録|"
  fi
  if [ "$reg" != "none" ]; then
    IFS=';' read -ra rows <<< "$reg"
    python3 "$SNAP" "$dir/ID設計.md" "${rows[@]}"
  fi
  local out rc
  out=$(TAZUNA_ROOT="$ROOT" python3 "$PY" "$dir" 2>&1); rc=$?
  out=$(grep -v '^WARN' <<<"$out")
  local got=ok; [ "$rc" -ne 0 ] && got=ng
  if [ "$got" = "$expect" ] && { [ -z "$needle" ] || grep -qF -- "$needle" <<<"$out"; }; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1)); echo "NG: $name（期待 $expect、結果 $got）"; echo "$out" | head -5
  fi
  rm -rf "$dir"
}

case_ "正しい設計書" ok "S-21-002_予約入力.md" "$good"
case_ "ファイル名に書類実体IDがない" ng "予約入力.md" "$good" "書類実体ID_名前.md"
case_ "ドキュメント体系にない書類ID" ng "S-99-001_何か.md" "${good//S-21-002/S-99-001}" "S-99 がドキュメント体系にありません"
case_ "見出しの形が違う" ng "S-21-002_予約入力.md" "${good/\#\# D-02002 画面項目定義/## 画面項目定義}" "D-ccsss 設計項目名"
case_ "カタログにない項番" ng "S-21-002_予約入力.md" "${good/D-02002/D-02999}" "D-02999 がカタログにありません"
case_ "項番と名前が合わない" ng "S-21-002_予約入力.md" "${good/画面項目定義/画面遷移}" "名前が違います"
case_ "その書類に書かない項目" ng "S-21-002_予約入力.md" "${good/D-02002 画面項目定義/D-05001 テーブル定義}" "S-16"
case_ "番号のない行" ng "S-21-002_予約入力.md" "${good/- \[2\] /- }" "「- [番号] 本文」になっていません"
case_ "見出しの中に欠番がある（行を消した）" ng "S-21-002_予約入力.md" "${good/- \[1\] 大人人数: プルダウン
/}" "[1] がありません"
case_ "見出しの中で番号が重複" ng "S-21-002_予約入力.md" "${good/\[2\]/[1]}" "重複しています"
case_ "別の見出しなら同じ番号でよい" ok "S-21-002_予約入力.md" "$good
## D-02003 項目の表示・活性条件

- [1] 子供料金がないツアーでは子供人数を表示しない
- [2] 順序は D-02002 の [2] → [1]
"
case_ "参照先の行がない" ng "S-21-002_予約入力.md" "$good
## D-02003 項目の表示・活性条件

- [1] 順序は D-02002 の [1] → [5]
" "S-21-002/D-02002/5 がありません"
case_ "見出しより前の行" ng "S-21-002_予約入力.md" "# S-21-002 画面設計書

- [1] 大人人数: プルダウン
" "どの見出しの下にもありません"

case_ "書き出し（ID設計.md）がない" ng "S-21-002_予約入力.md" "$good" "ID設計.md" "none"
case_ "書類一覧に載っていない" ng "S-21-002_予約入力.md" "$good" "S-21-002 が書類一覧にありません" "S-21-001|検索|S-22-001;S-22-001|予約登録|"
case_ "ファイル名が書類一覧の名前と合わない" ng "S-21-002_予約入力.md" "$good" "ファイル名が書類一覧の名前" "S-21-002|予約確認|S-22-001;S-22-001|予約登録|"
case_ "機能別の書類に機能がない" ng "S-26-001_予約登録.md" "# S-26-001 テスト仕様書

## D-15001 テスト観点・ケース

- [1] 同じ受付トークンで2回確定しても、予約は1件だけ登録される
" "「機能」が空です" "S-26-001|予約登録|;S-22-001|予約登録|"
case_ "機能の処理設計書が一覧にない" ng "S-26-001_予約登録.md" "# S-26-001 テスト仕様書

## D-15001 テスト観点・ケース

- [1] 同じ受付トークンで2回確定しても、予約は1件だけ登録される
" "機能 S-22-009 が書類一覧にありません" "S-26-001|予約登録|S-22-009"
case_ "機能が正しく書かれている（まだファイルのない処理設計書は警告だけ）" ok "S-26-001_予約登録.md" "# S-26-001 テスト仕様書

## D-15001 テスト観点・ケース

- [1] 同じ受付トークンで2回確定しても、予約は1件だけ登録される
" "" "S-26-001|予約登録|S-22-001;S-22-001|予約登録|"

# base から行IDが消えたら止まる（一時的な git リポジトリで確かめる）
repo=$(mktemp -d)
( cd "$repo" && git init -q && mkdir -p docs/design && printf '%s' "$good" > docs/design/S-21-002_予約入力.md \
  && python3 "$SNAP" docs/design/ID設計.md "S-21-002|予約入力|S-22-002" "S-22-002|予約登録|" \
  && git add -A && git -c user.email=t@t -c user.name=t commit -qm base \
  && printf '%s' "$good" | grep -v '^- \[2\]' > docs/design/S-21-002_予約入力.md )
out=$(TAZUNA_ROOT="$repo" python3 "$PY" "$repo/docs/design" --base HEAD 2>&1); rc=$?
if [ "$rc" -ne 0 ] && grep -qF "S-21-002/D-02002/2 が HEAD から消えています" <<<"$out"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: 消えた行ID"; echo "$out" | head -5; fi
printf '%s' "${good/備考: テキストエリア、最大80文字/（廃止）備考の80文字の制限は要件から外れた}" > "$repo/docs/design/S-21-002_予約入力.md"
out=$(TAZUNA_ROOT="$repo" python3 "$PY" "$repo/docs/design" --base HEAD 2>&1); rc=$?
if [ "$rc" -eq 0 ]; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: 廃止にした行は通る"; echo "$out" | head -5; fi
# base 側で分かれた後に足された行は、この変更が消したことにしない（PR のブランチが main より古いとき）
g() { git -C "$repo" -c user.email=t@t -c user.name=t "$@"; }
g add -A; g commit -qm feature-start
main=$(g branch --show-current); g branch -q feature
printf '%s\n- [3] 後から main で足した行\n' "$(cat "$repo/docs/design/S-21-002_予約入力.md")" > "$repo/docs/design/S-21-002_予約入力.md"
g commit -qam main-added; g checkout -q feature
out=$(TAZUNA_ROOT="$repo" python3 "$PY" "$repo/docs/design" --base "$main" 2>&1); rc=$?
if [ "$rc" -eq 0 ]; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: 分かれた後に base で足した行は消えたことにしない"; echo "$out" | head -5; fi
rm -rf "$repo"

case_ "行に図を付けられる（図の中の - や ## は行・見出しにしない）" ok "S-21-002_予約入力.md" '# S-21-002 画面設計書：予約入力

## D-02002 画面項目定義

- [1] 画面の項目の並び
  ```mermaid
  flowchart LR
  - [5] これは図の中
  ## これも図の中
  ```
- [2] 備考: テキストエリア、最大80文字
'
case_ "どの行にも付いていない図" ng "S-21-002_予約入力.md" '# S-21-002 画面設計書：予約入力

## D-02002 画面項目定義

- [1] 大人人数: プルダウン

```mermaid
flowchart LR
```
' "図や \`\`\` のブロックがどの行にも付いていません"

case_ "行が指すファイルがなければ止める" ng "S-21-002_予約入力.md" '# S-21-002 画面設計書：予約入力

## D-02002 画面項目定義

- [1] 項目の意味は docs/requirements/transfer.md を読む
' "行が指すファイル docs/requirements/transfer.md がありません"
case_ "行が指すファイルがあれば通す" ok "S-21-002_予約入力.md" '# S-21-002 画面設計書：予約入力

## D-02002 画面項目定義

- [1] 命名は docs/conventions.md に合わせる
'

# ★: 共通の必須の見出しが空なのに、機能の書類が同じ設計項目を決めていれば警告する（止めない）
d=$(mktemp -d)
printf '# S-11-001 方式設計書：方式設計書\n\n## D-06001 トランザクション境界\n\n- [1] サービスのメソッド単位\n' > "$d/S-11-001_方式設計書.md"
printf '# S-22-001 処理設計書：予約登録\n\n## D-06003 排他制御の方式\n\n- [1] 版番号で更新する\n' > "$d/S-22-001_予約登録.md"
python3 "$SNAP" "$d/ID設計.md" "S-11-001|方式設計書|" "S-22-001|予約登録|"
out=$(TAZUNA_ROOT="$ROOT" python3 "$PY" "$d" 2>&1); rc=$?
if [ "$rc" -eq 0 ] && grep -qF "★ D-06003 排他制御の方式 が空なのに、機能の書類（S-22-001）" <<<"$out"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: ★ を警告する"; echo "$out" | grep -E "★|ERROR" | head -3; fi
printf '\n## D-06003 排他制御の方式\n\n- [1] 機能ごとに処理設計書で決める\n' >> "$d/S-11-001_方式設計書.md"
out=$(TAZUNA_ROOT="$ROOT" python3 "$PY" "$d" 2>&1)
if ! grep -qF "★ D-06003" <<<"$out"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: 共通に書けば ★ は消える"; fi
rm -rf "$d"

# CRUD の行に出てくる名前を DDL と突き合わせ、テーブルにも列にもない名前を警告する（止めない）
r=$(mktemp -d); d="$r/docs/design"; mkdir -p "$d" "$r/db/schema"
printf 'CREATE TABLE RESERVE (\n    RESERVE_NO CHAR(13) NOT NULL,\n    VERSION NUMBER(9) NOT NULL,\n    CONSTRAINT PK_RESERVE PRIMARY KEY (RESERVE_NO)\n);\n' > "$r/db/schema/RESERVE.sql"
printf '# S-22-001 処理設計書：予約取消\n\n## D-05006 CRUD\n\n- [1] RESERVE の VERSION を UPDATE する\n- [2] TOURINFO を読み、残席を更新する\n- [3] J110 とは同時に動かない\n' > "$d/S-22-001_予約取消.md"
python3 "$SNAP" "$d/ID設計.md" "S-22-001|予約取消|"
out=$(TAZUNA_ROOT="$r" python3 "$PY" "$d" 2>&1); rc=$?
if [ "$rc" -eq 0 ] && grep -qF "S-22-001/D-05006/2（CRUD）の TOURINFO が DDL にありません" <<<"$out"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: DDL にないテーブルを警告する"; echo "$out" | head -5; fi
if ! grep -qE "（CRUD）の (RESERVE|VERSION|UPDATE|J110) " <<<"$out"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: DDL のテーブル・列、SQL の言葉、ジョブ ID は警告しない"; fi
out=$(cd "$r" && python3 -c "import sys; sys.path.insert(0, '$ROOT/scripts/design'); import gaps; print(gaps.crud('.', 'docs/design')[0])")
if grep -qF "'RESERVE': ['S-22-001/D-05006/1']" <<<"$out"; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "NG: テーブルから CRUD の行を逆引きできる: $out"; fi
rm -rf "$r"

echo "design-docs: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
