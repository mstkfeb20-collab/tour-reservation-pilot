# 作業一覧：RESERVE

> ID 設計から転記した作業。実装の issue から参照する。

<!-- tazuna:design S-16-001 begin src=44ecc495273a（scripts/design/transcribe.py が作る。手で直さない） -->
## 型・API・DB 制約で書けなくする

- [ ] RESERVE.RESERVE_NO VARCHAR2(13)（S-16-001-001・テーブル定義）
- [ ] RESERVE.TOUR_CODE CHAR(8)（S-16-001-002・テーブル定義）
- [ ] RESERVE.MEMBER_NO CHAR(10)（S-16-001-003・テーブル定義）
- [ ] RESERVE.ADULT_COUNT NUMBER(1)、RESERVE.CHILD_COUNT NUMBER(1)（S-16-001-004・テーブル定義）
- [ ] RESERVE.SUM_PRICE NUMBER(9)（S-16-001-005・テーブル定義）
- [ ] RESERVE.TRANSFER CHAR(1)（S-16-001-006・テーブル定義）
- [ ] RESERVE.PAY_DUE_DATE DATE（S-16-001-007・テーブル定義）
- [ ] RESERVE.REPRESENTATIVE_NAME NVARCHAR2(20)、RESERVE.REPRESENTATIVE_KANA NVARCHAR2(40)（S-16-001-008・テーブル定義）
- [ ] RESERVE.BIRTH_DATE DATE（S-16-001-009・テーブル定義）
- [ ] RESERVE.TEL VARCHAR2(11)、RESERVE.MAIL VARCHAR2(256)（S-16-001-010・テーブル定義）
- [ ] RESERVE.REMARKS VARCHAR2(240 BYTE)。80文字 × UTF-8 最大3バイト（S-16-001-011・テーブル定義）
- [ ] RESERVE.PASSPORT_FILE_ID VARCHAR2(36)（S-16-001-012・テーブル定義）
- [ ] RESERVE.REQUEST_TOKEN VARCHAR2(36)（S-16-001-013・テーブル定義）
- [ ] RESERVE.VERSION NUMBER(9)（S-16-001-014・テーブル定義）
- [ ] RESERVE.PAID_DATE DATE、RESERVE.PAID_AMOUNT NUMBER(9)、RESERVE.LATE_PAYMENT_FLAG CHAR(1)（S-16-001-015・テーブル定義）
- [ ] RESERVE の主キーは RESERVE_NO（S-16-001-016・主キー・一意制約）
- [ ] RESERVE.REQUEST_TOKEN に一意制約を付ける（S-16-001-017・主キー・一意制約）
- [ ] RESERVE.TOUR_CODE は TOURINFO.TOUR_CODE を参照する（S-16-001-018・外部キー・参照整合性）
- [ ] RESERVE.MEMBER_NO は MEMBER.MEMBER_NO を参照する（S-16-001-019・外部キー・参照整合性）
- [ ] RESERVE.TRANSFER は NOT NULL、初期値 '0'（S-16-001-020・NULL可否・初期値）
- [ ] RESERVE.REMARKS と PASSPORT_FILE_ID は NULL 可、それ以外の列は NOT NULL（S-16-001-021・NULL可否・初期値）
- [ ] PAID_DATE・PAID_AMOUNT は未振込の間 NULL（S-16-001-022・NULL可否・初期値）
- [ ] LATE_PAYMENT_FLAG は NOT NULL、初期値 '0'（S-16-001-023・NULL可否・初期値）

## Lint を足す

- [ ] CREATED_BY・UPDATED_BY には、お客様なら会員番号、窓口担当なら社員番号を入れる（S-16-001-026・監査項目）
- [ ] J110 が更新した行の UPDATED_BY は 'J110'（S-16-001-027・監査項目）
- [ ] エンティティの桁数・NULL 可否は DDL と一致させる（S-16-001-032・DB定義とコードの一致）
- [ ] Reservation エンティティの桁数・NULL 可否は RESERVE の DDL と一致させる（S-16-001-033・DB定義とコードの一致）

## 動かして測り、PR に結果を添える

- [ ] RESERVE に 顧客番号＋出発日 の複合索引を作る（S-16-001-024・インデックス）
- [ ] RESERVE に MEMBER_NO＋TOUR_CODE の索引を作る（重複チェック用）（S-16-001-025・インデックス）

## 承認されているか確かめる

- [ ] 予約は出発日から7年保持し、その後は退避して削除する（S-16-001-030・保持期間・削除）
- [ ] パスポートの写しは出発日の30日後に削除する（S-16-001-031・保持期間・削除）
<!-- tazuna:design S-16-001 end -->
