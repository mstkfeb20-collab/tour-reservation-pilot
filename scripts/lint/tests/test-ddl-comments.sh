#!/usr/bin/env bash
# ddl_comments.py（COMMON-010）の自己テスト。DDL を1つずつ置き、期待どおり止まるかを確かめる。
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT="$PWD"; PY="$ROOT/scripts/lint/common/ddl_comments.py"; SNAP="$ROOT/scripts/lint/tests/snapshot-for-test.py"
pass=0; fail=0

# case_ <名前> <期待（ok|ng）> <DDL> [期待するメッセージの一部]
case_() {
  local name="$1" expect="$2" sql="$3" needle="${4:-}"
  local w; w=$(mktemp -d); mkdir -p "$w/db/schema" "$w/docs/design"
  printf '%s' "$sql" > "$w/db/schema/T.sql"
  python3 "$SNAP" "$w/docs/design/ID設計.md" "S-15-001|コード定義書|"
  printf '# S-15-001 コード定義書：コード定義書\n\n## D-05005 コード値（区分値）の定義\n\n- [1] 振込状況: 0 未振込、1 振込済、9 取消\n- [2] （廃止）旧区分\n' > "$w/docs/design/S-15-001_コード定義書.md"
  local out rc; out=$(python3 "$PY" "$w" 2>&1); rc=$?
  out=$(grep -v '^WARN' <<<"$out")
  local got=ok; [ "$rc" -ne 0 ] && got=ng
  if [ "$got" = "$expect" ] && { [ -z "$needle" ] || grep -qF -- "$needle" <<<"$out"; }; then pass=$((pass + 1))
  else fail=$((fail + 1)); echo "NG: $name（期待 $expect、結果 $got）"; echo "$out" | sed 's/^/    /'; fi
  rm -rf "$w"
}

good="CREATE TABLE R (
  NO CHAR(10) NOT NULL,
  TRANSFER CHAR(1) NOT NULL,
  CONSTRAINT PK_R PRIMARY KEY (NO),
  CONSTRAINT CK_R CHECK (TRANSFER IN ('0','1','9'))
);
COMMENT ON TABLE R IS '予約';
COMMENT ON COLUMN R.NO IS '予約番号';
COMMENT ON COLUMN R.TRANSFER IS '振込状況。値の意味は S-15-001/D-05005/1';
"
case_ "説明がそろっている" ok "$good"
case_ "テーブルの説明がない" ng "$(grep -v 'ON TABLE' <<<"$good")" "テーブル R に説明"
case_ "列の説明がない" ng "$(grep -v 'R.NO IS' <<<"$good")" "列 R.NO に説明"
case_ "空の説明" ng "${good/'予約番号'/''}" "列 R.NO に説明"
case_ "区分値の列が設計書の行を指さない" ng "${good/値の意味は S-15-001\/D-05005\/1/0 未振込 1 振込済}" "値の意味を決めた設計書の行"
case_ "指した行がない" ng "${good/D-05005\/1/D-05005\/7}" "S-15-001/D-05005/7 が設計書にありません"
case_ "廃止の行は指せない" ng "${good/D-05005\/1/D-05005\/2}" "が設計書にありません"
case_ "列定義の COMMENT でもよい" ok "CREATE TABLE R (
  NO CHAR(10) NOT NULL COMMENT '予約番号',
  NOTE VARCHAR(80) COMMENT '備考, 最大80文字',
  PRIMARY KEY (NO)
) COMMENT='予約';
"
case_ "SQL のコメント（--）は説明にならない" ng "CREATE TABLE R (
  NO CHAR(10) NOT NULL -- COMMENT '予約番号'
) COMMENT='予約';
" "列 R.NO に説明"

echo "ddl-comments: ${pass} 件成功 / ${fail} 件失敗"
[ "$fail" -eq 0 ]
