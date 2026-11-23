# S-16-002 テーブル定義書：TRANSFER_IMPORT

> 見出しの下に、1行に1つの決定事項を「- 行ID 本文」で書く。行IDはこのファイルの末尾の次の番号（例 S-16-002-001）。書くことがない見出しには「該当なし（理由）」と書く。

## D-05001 テーブル定義

<!-- （必須） -->
- [1] TRANSFER_IMPORT.ACCOUNT_DATE DATE、TRANSFER_IMPORT.INQUIRY_NO CHAR(6)
- [2] TRANSFER_IMPORT.AMOUNT NUMBER(10)
- [3] TRANSFER_IMPORT.PAYER_NAME VARCHAR2(48)
- [4] TRANSFER_IMPORT.RESERVE_NO VARCHAR2(13)
- [5] TRANSFER_IMPORT.RESULT CHAR(2)
- [6] TRANSFER_IMPORT.FILE_NAME VARCHAR2(64)

## D-05002 主キー・一意制約

<!-- （必須） -->
- [1] TRANSFER_IMPORT の主キーは ACCOUNT_DATE＋INQUIRY_NO

## D-05003 外部キー・参照整合性

<!-- （必須） -->

## D-05004 NULL可否・初期値

<!-- （必須） -->
- [1] TRANSFER_IMPORT.RESERVE_NO は、予約番号が読み取れなかった明細では NULL

## D-05008 インデックス

<!-- （必須） -->

## D-05010 監査項目

<!-- （必須） このテーブルの監査列に入れる値 -->

## D-05011 データ量・増加見込み

<!-- （必須） -->
- [1] 振込明細は平常1日300件、繁忙期は最大3千件

## D-05012 保持期間・削除

<!-- （必須） -->
- [1] TRANSFER_IMPORT は7年保持する

## D-05014 マスタとトランザクションの区別

<!-- （必須） -->

## D-05015 DB定義とコードの一致

<!-- （必須） -->
