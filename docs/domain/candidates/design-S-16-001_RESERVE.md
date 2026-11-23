# 不変条件の候補：RESERVE

> ID 設計から転記した、システム共通の業務ルールの候補。正本ではない。

<!-- tazuna:design S-16-001 begin src=44ecc495273a（scripts/design/transcribe.py が作る。手で直さない） -->
## S-16-001 テーブル定義書：RESERVE

社員が各行の判定（承認・却下・保留）を決め、承認したものを invariants.md に「防ぐ層」「担保」付きで移す。

- RESERVE の主キーは RESERVE_NO（S-16-001-016・主キー・一意制約）　判定: 未
- RESERVE.REQUEST_TOKEN に一意制約を付ける（S-16-001-017・主キー・一意制約）　判定: 未
<!-- tazuna:design S-16-001 end -->
