# 作業一覧：TRANSFER_IMPORT

> ID 設計から転記した作業。実装の issue から参照する。

<!-- tazuna:design S-16-002 begin src=2efdf072264d（scripts/design/transcribe.py が作る。手で直さない） -->
## 型・API・DB 制約で書けなくする

- [ ] TRANSFER_IMPORT.ACCOUNT_DATE DATE、TRANSFER_IMPORT.INQUIRY_NO CHAR(6)（S-16-002/D-05001/1・テーブル定義）
- [ ] TRANSFER_IMPORT.AMOUNT NUMBER(10)（S-16-002/D-05001/2・テーブル定義）
- [ ] TRANSFER_IMPORT.PAYER_NAME VARCHAR2(48)（S-16-002/D-05001/3・テーブル定義）
- [ ] TRANSFER_IMPORT.RESERVE_NO VARCHAR2(13)（S-16-002/D-05001/4・テーブル定義）
- [ ] TRANSFER_IMPORT.RESULT CHAR(2)（S-16-002/D-05001/5・テーブル定義）
- [ ] TRANSFER_IMPORT.FILE_NAME VARCHAR2(64)（S-16-002/D-05001/6・テーブル定義）
- [ ] TRANSFER_IMPORT の主キーは ACCOUNT_DATE＋INQUIRY_NO（S-16-002/D-05002/1・主キー・一意制約）
- [ ] TRANSFER_IMPORT.RESERVE_NO は、予約番号が読み取れなかった明細では NULL（S-16-002/D-05004/1・NULL可否・初期値）

## 承認されているか確かめる

- [ ] TRANSFER_IMPORT は7年保持する（S-16-002/D-05012/1・保持期間・削除）
<!-- tazuna:design S-16-002 end -->
