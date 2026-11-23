#!/usr/bin/env bash
# すべてのLintチェックを実行する。
#   scripts/lint/run-all.sh          全チェック
#   scripts/lint/run-all.sh --fast   *.slow.sh を除いて実行（hooksから呼ぶ用）
#
# チェックの追加方法:
#   - 汎用チェック（型として配る）     → scripts/lint/common/<名前>.sh
#   - 業務固有チェック（案件ごとに作る） → scripts/lint/domain/<名前>.sh
#   ファイルを置くだけで自動的に実行される。時間がかかるものは <名前>.slow.sh にする。
set -u

cd "$(dirname "$0")/../.." || exit 2
export TAZUNA_ROOT="$PWD"

FAST=0
[ "${1:-}" = "--fast" ] && FAST=1

failed=()
ran=0
for check in scripts/lint/common/*.sh scripts/lint/domain/*.sh; do
  [ -f "$check" ] || continue
  if [ "$FAST" -eq 1 ] && [[ "$check" == *.slow.sh ]]; then
    continue
  fi
  ran=$((ran + 1))
  if ! bash "$check"; then
    failed+=("$check")
  fi
done

echo "----"
if [ "${#failed[@]}" -gt 0 ]; then
  echo "Lint NG: ${#failed[@]}/${ran} 件のチェックが失敗しました" >&2
  for f in "${failed[@]}"; do echo "  - $f" >&2; done
  exit 1
fi
echo "Lint OK: ${ran} 件のチェックをすべて通過しました"
