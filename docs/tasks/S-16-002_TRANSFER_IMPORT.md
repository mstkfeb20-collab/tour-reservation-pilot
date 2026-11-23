# 作業一覧：TRANSFER_IMPORT

> ID 設計から転記した作業。実装の issue から参照する。

<!-- tazuna:design S-16-002 begin src=e14105585e86（scripts/design/transcribe.py が作る。手で直さない） -->
## 型・API・DB 制約で書けなくする

- [ ] TRANSFER_IMPORT.ACCOUNT_DATE DATE、TRANSFER_IMPORT.INQUIRY_NO CHAR(6)（S-16-002-001・テーブル定義）
- [ ] TRANSFER_IMPORT.AMOUNT NUMBER(10)（S-16-002-002・テーブル定義）
- [ ] TRANSFER_IMPORT.PAYER_NAME VARCHAR2(48)（S-16-002-003・テーブル定義）
- [ ] TRANSFER_IMPORT.RESERVE_NO VARCHAR2(13)（S-16-002-004・テーブル定義）
- [ ] TRANSFER_IMPORT.RESULT CHAR(2)（S-16-002-005・テーブル定義）
- [ ] TRANSFER_IMPORT.FILE_NAME VARCHAR2(64)（S-16-002-006・テーブル定義）
- [ ] TRANSFER_IMPORT の主キーは ACCOUNT_DATE＋INQUIRY_NO（S-16-002-007・主キー・一意制約）
- [ ] TRANSFER_IMPORT.RESERVE_NO は、予約番号が読み取れなかった明細では NULL（S-16-002-008・NULL可否・初期値）

## 承認されているか確かめる

- [ ] TRANSFER_IMPORT は7年保持する（S-16-002-010・保持期間・削除）
<!-- tazuna:design S-16-002 end -->
