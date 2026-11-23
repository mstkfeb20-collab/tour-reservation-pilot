# ルール違反の記録

レビューで指摘した人が1行ずつ追記する。月に1回、案件リーダーが見返してハーネスを直す（`harness/GUIDE.md#月次の見直し`）。

- 防ぐ層: `設計`／`Lint`／`テスト`／`実行検証`／`文章`／`hooks` のどれか（`scripts/lint/common/rule-log-format.sh` が検査する）
- 対応: 作ったLint・テスト・変えた設計のパス

| 日付 | 内容 | 原因 | 防ぐ層 | 対応 | 記録者 |
| --- | --- | --- | --- | --- | --- |
| 2026-11-21 | （見本）金額を double で計算していた | 不変条件が文章にしかなかった | Lint | scripts/lint/domain/java-money-no-float.sh を追加 | tazuna |
