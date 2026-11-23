# 不変条件の候補：TRANSFER_IMPORT

> ID 設計から転記した、システム共通の業務ルールの候補。正本ではない。

<!-- tazuna:design S-16-002 begin src=e14105585e86（scripts/design/transcribe.py が作る。手で直さない） -->
## S-16-002 テーブル定義書：TRANSFER_IMPORT

社員が各行の判定（承認・却下・保留）を決め、承認したものを invariants.md に「防ぐ層」「担保」付きで移す。

- TRANSFER_IMPORT の主キーは ACCOUNT_DATE＋INQUIRY_NO（S-16-002-007・主キー・一意制約）　判定: 未
<!-- tazuna:design S-16-002 end -->
