#!/usr/bin/env bash
# 【業務固有チェックの見本】INV-001 金額は double / float で扱わない。
# 案件では、docs/domain/invariants.md の不変条件ごとにこのようなチェックを作る。
source "$(dirname "$0")/../lib.sh"

SRC="$TAZUNA_ROOT/src/main/java"
[ -d "$SRC" ] || lint_finish

# 金額らしい名前（amount, price, fee, total, money, yen, cost）を double/float で宣言している箇所
pattern='\b(double|float|Double|Float)\b[[:space:]]+[A-Za-z_]*([Aa]mount|[Pp]rice|[Ff]ee|[Tt]otal|[Mm]oney|[Yy]en|[Cc]ost)[A-Za-z_]*'

while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  loc="${hit%%:*}"; rest="${hit#*:}"; line="${rest%%:*}"
  lint_error "INV-001" "${loc#"$TAZUNA_ROOT"/}:$line" \
    "金額を double / float で扱っています" \
    "浮動小数点は丸め誤差で金額が1円ずれることがあります" \
    "com.example.domain.Money を使ってください（例: Money.yen(1000)）" \
    "docs/domain/invariants.md#INV-001"
done < <(grep -rnE "$pattern" "$SRC" --include='*.java' 2>/dev/null)

lint_finish
