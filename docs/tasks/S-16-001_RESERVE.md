# 作業一覧：RESERVE

> ID 設計から転記した作業。実装の issue から参照する。

<!-- tazuna:design S-16-001 begin src=30f01df2f872（scripts/design/transcribe.py が作る。手で直さない） -->
## 型・API・DB 制約で書けなくする

- [ ] RESERVE.RESERVE_NO VARCHAR2(13)（S-16-001/D-05001/1・テーブル定義）
- [ ] RESERVE.TOUR_CODE CHAR(8)（S-16-001/D-05001/2・テーブル定義）
- [ ] RESERVE.MEMBER_NO CHAR(10)（S-16-001/D-05001/3・テーブル定義）
- [ ] RESERVE.ADULT_COUNT NUMBER(1)、RESERVE.CHILD_COUNT NUMBER(1)（S-16-001/D-05001/4・テーブル定義）
- [ ] RESERVE.SUM_PRICE NUMBER(9)（S-16-001/D-05001/5・テーブル定義）
- [ ] RESERVE.TRANSFER CHAR(1)（S-16-001/D-05001/6・テーブル定義）
- [ ] RESERVE.PAY_DUE_DATE DATE（S-16-001/D-05001/7・テーブル定義）
- [ ] RESERVE.REPRESENTATIVE_NAME NVARCHAR2(20)、RESERVE.REPRESENTATIVE_KANA NVARCHAR2(40)（S-16-001/D-05001/8・テーブル定義）
- [ ] RESERVE.BIRTH_DATE DATE（S-16-001/D-05001/9・テーブル定義）
- [ ] RESERVE.TEL VARCHAR2(11)、RESERVE.MAIL VARCHAR2(256)（S-16-001/D-05001/10・テーブル定義）
- [ ] RESERVE.REMARKS VARCHAR2(240 BYTE)。80文字 × UTF-8 最大3バイト（S-16-001/D-05001/11・テーブル定義）
- [ ] RESERVE.PASSPORT_FILE_ID VARCHAR2(36)（S-16-001/D-05001/12・テーブル定義）
- [ ] RESERVE.REQUEST_TOKEN VARCHAR2(36)（S-16-001/D-05001/13・テーブル定義）
- [ ] RESERVE.VERSION NUMBER(9)（S-16-001/D-05001/14・テーブル定義）
- [ ] RESERVE.PAID_DATE DATE、RESERVE.PAID_AMOUNT NUMBER(9)、RESERVE.LATE_PAYMENT_FLAG CHAR(1)（S-16-001/D-05001/15・テーブル定義）
- [ ] RESERVE の主キーは RESERVE_NO（S-16-001/D-05002/1・主キー・一意制約）
- [ ] RESERVE.REQUEST_TOKEN に一意制約を付ける（S-16-001/D-05002/2・主キー・一意制約）
- [ ] RESERVE.TOUR_CODE は TOURINFO.TOUR_CODE を参照する（S-16-001/D-05003/1・外部キー・参照整合性）
- [ ] RESERVE.MEMBER_NO は MEMBER.MEMBER_NO を参照する（S-16-001/D-05003/2・外部キー・参照整合性）
- [ ] RESERVE.TRANSFER は NOT NULL、初期値 '0'（S-16-001/D-05004/1・NULL可否・初期値）
- [ ] RESERVE.REMARKS と PASSPORT_FILE_ID は NULL 可、それ以外の列は NOT NULL（S-16-001/D-05004/2・NULL可否・初期値）
- [ ] PAID_DATE・PAID_AMOUNT は未振込の間 NULL（S-16-001/D-05004/3・NULL可否・初期値）
- [ ] LATE_PAYMENT_FLAG は NOT NULL、初期値 '0'（S-16-001/D-05004/4・NULL可否・初期値）

## Lint を足す

- [ ] CREATED_BY・UPDATED_BY には、お客様なら会員番号、窓口担当なら社員番号を入れる（S-16-001/D-05010/1・監査項目）
- [ ] J110 が更新した行の UPDATED_BY は 'J110'（S-16-001/D-05010/2・監査項目）
- [ ] エンティティの桁数・NULL 可否は DDL と一致させる（S-16-001/D-05015/1・DB定義とコードの一致）
- [ ] Reservation エンティティの桁数・NULL 可否は RESERVE の DDL と一致させる（S-16-001/D-05015/2・DB定義とコードの一致）

## 動かして測り、PR に結果を添える

- [ ] RESERVE に 顧客番号＋出発日 の複合索引を作る（S-16-001/D-05008/1・インデックス）
- [ ] RESERVE に MEMBER_NO＋TOUR_CODE の索引を作る（重複チェック用）（S-16-001/D-05008/2・インデックス）

## 承認されているか確かめる

- [ ] 予約は出発日から7年保持し、その後は退避して削除する（S-16-001/D-05012/1・保持期間・削除）
- [ ] パスポートの写しは出発日の30日後に削除する（S-16-001/D-05012/2・保持期間・削除）
<!-- tazuna:design S-16-001 end -->
