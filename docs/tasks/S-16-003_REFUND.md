# 作業一覧：REFUND

> ID 設計から転記した作業。実装の issue から参照する。

<!-- tazuna:design S-16-003 begin src=542836306ecc（scripts/design/transcribe.py が作る。手で直さない） -->
## Lint を足す

- [ ] CREATED_AT・CREATED_BY・UPDATED_AT・UPDATED_BY を持つ（S-16-003/D-05010/1・監査項目）
- [ ] 列・型・制約は db/schema/REFUND.sql が正（S-16-003/D-05015/1・DB定義とコードの一致）

## 動かして測り、PR に結果を添える

- [ ] 予約番号に索引を張る（予約ごとの返金を引くため）（S-16-003/D-05008/1・インデックス）

## 承認されているか確かめる

- [ ] 7年保持し、過ぎたら物理削除する（S-16-003/D-05012/1・保持期間・削除）
<!-- tazuna:design S-16-003 end -->
