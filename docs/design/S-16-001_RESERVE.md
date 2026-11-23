# S-16-001 テーブル定義書：RESERVE

> 見出しの下に、1行に1つの決定事項を「- 行ID 本文」で書く。行IDはこのファイルの末尾の次の番号（例 S-16-001-001）。書くことがない見出しには「該当なし（理由）」と書く。

## D-05001 テーブル定義

<!-- （必須） -->
- [1] RESERVE.RESERVE_NO VARCHAR2(13)
- [2] RESERVE.TOUR_CODE CHAR(8)
- [3] RESERVE.MEMBER_NO CHAR(10)
- [4] RESERVE.ADULT_COUNT NUMBER(1)、RESERVE.CHILD_COUNT NUMBER(1)
- [5] RESERVE.SUM_PRICE NUMBER(9)
- [6] RESERVE.TRANSFER CHAR(1)
- [7] RESERVE.PAY_DUE_DATE DATE
- [8] RESERVE.REPRESENTATIVE_NAME NVARCHAR2(20)、RESERVE.REPRESENTATIVE_KANA NVARCHAR2(40)
- [9] RESERVE.BIRTH_DATE DATE
- [10] RESERVE.TEL VARCHAR2(11)、RESERVE.MAIL VARCHAR2(256)
- [11] RESERVE.REMARKS VARCHAR2(240 BYTE)。80文字 × UTF-8 最大3バイト
- [12] RESERVE.PASSPORT_FILE_ID VARCHAR2(36)
- [13] RESERVE.REQUEST_TOKEN VARCHAR2(36)
- [14] RESERVE.VERSION NUMBER(9)
- [15] RESERVE.PAID_DATE DATE、RESERVE.PAID_AMOUNT NUMBER(9)、RESERVE.LATE_PAYMENT_FLAG CHAR(1)

## D-05002 主キー・一意制約

<!-- （必須） -->
- [1] RESERVE の主キーは RESERVE_NO
- [2] RESERVE.REQUEST_TOKEN に一意制約を付ける

## D-05003 外部キー・参照整合性

<!-- （必須） -->
- [1] RESERVE.TOUR_CODE は TOURINFO.TOUR_CODE を参照する
- [2] RESERVE.MEMBER_NO は MEMBER.MEMBER_NO を参照する

## D-05004 NULL可否・初期値

<!-- （必須） -->
- [1] RESERVE.TRANSFER は NOT NULL、初期値 '0'
- [2] RESERVE.REMARKS と PASSPORT_FILE_ID は NULL 可、それ以外の列は NOT NULL
- [3] PAID_DATE・PAID_AMOUNT は未振込の間 NULL
- [4] LATE_PAYMENT_FLAG は NOT NULL、初期値 '0'

## D-05008 インデックス

<!-- （必須） -->
- [1] RESERVE に 顧客番号＋出発日 の複合索引を作る
- [2] RESERVE に MEMBER_NO＋TOUR_CODE の索引を作る（重複チェック用）

## D-05010 監査項目

<!-- （必須） このテーブルの監査列に入れる値 -->
- [1] CREATED_BY・UPDATED_BY には、お客様なら会員番号、窓口担当なら社員番号を入れる
- [2] J110 が更新した行の UPDATED_BY は 'J110'

## D-05011 データ量・増加見込み

<!-- （必須） -->
- [1] 予約は年間約30万件増える。照会は直近2年分が対象
- [2] RESERVE は年間約30万件増える。販売開始日は1時間に最大3千件登録される

## D-05012 保持期間・削除

<!-- （必須） -->
- [1] 予約は出発日から7年保持し、その後は退避して削除する
- [2] パスポートの写しは出発日の30日後に削除する

## D-05014 マスタとトランザクションの区別

<!-- （必須） -->

## D-05015 DB定義とコードの一致

<!-- （必須） -->
- [1] エンティティの桁数・NULL 可否は DDL と一致させる
- [2] Reservation エンティティの桁数・NULL 可否は RESERVE の DDL と一致させる
