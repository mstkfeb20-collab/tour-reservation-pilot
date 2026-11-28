# 背景知識

> ID 設計から転記した、判断の材料になる事実。守らせるルールではない。

<!-- tazuna:design S-12-001 begin src=9220d4639725（scripts/design/transcribe.py が作る。手で直さない） -->
## S-12-001 画面共通設計書：画面共通設計書

- 画面・メッセージ・帳票では「取消」で統一し、「キャンセル」は使わない（S-12-001/D-02011/1・文言・ラベル）
- 「振込済」は「入金済」と書かない。銀行振込以外の入金手段がないため（S-12-001/D-02011/2・文言・ラベル）
<!-- tazuna:design S-12-001 end -->

<!-- tazuna:design S-16-001 begin src=0b2add49521b（scripts/design/transcribe.py が作る。手で直さない） -->
## S-16-001 テーブル設計書：RESERVE

- 予約は年間約30万件増える。照会は直近2年分が対象（S-16-001/D-05011/1・データ量・増加見込み）
- RESERVE は年間約30万件増える。販売開始日は1時間に最大3千件登録される（S-16-001/D-05011/2・データ量・増加見込み）
<!-- tazuna:design S-16-001 end -->

<!-- tazuna:design S-16-002 begin src=fad89f13ca30（scripts/design/transcribe.py が作る。手で直さない） -->
## S-16-002 テーブル設計書：TRANSFER_IMPORT

- 振込明細は平常1日300件、繁忙期は最大3千件（S-16-002/D-05011/1・データ量・増加見込み）
<!-- tazuna:design S-16-002 end -->

<!-- tazuna:design S-17-001 begin src=fa6d0a77c221（scripts/design/transcribe.py が作る。手で直さない） -->
## S-17-001 共通部品設計書：共通部品設計書

- 共通部品は Money（金額）・BusinessCalendar（営業日）・CodeValue（区分値）（S-17-001/D-14006/1・共通部品の一覧）
<!-- tazuna:design S-17-001 end -->

<!-- tazuna:design S-18-001 begin src=442f5d3edf91（scripts/design/transcribe.py が作る。手で直さない） -->
## S-18-001 バッチ共通設計書：バッチ共通設計書

- /TOUR/NIGHTLY: J110 振込取込 → J120 残席突合 → J310 予約一覧表（S-18-001/D-08001/1・ジョブ一覧・ジョブネット）
<!-- tazuna:design S-18-001 end -->

<!-- tazuna:design S-19-001 begin src=ed7d14e89eb6（scripts/design/transcribe.py が作る。手で直さない） -->
## S-19-001 非機能設計書：非機能設計書

- 性能は本番相当（ツアー5千件・予約60万件）のデータで測る（S-19-001/D-12007/1・性能測定の条件）
<!-- tazuna:design S-19-001 end -->

<!-- tazuna:design S-22-001 begin src=710c8ec12034（scripts/design/transcribe.py が作る。手で直さない） -->
## S-22-001 処理設計書：振込データ取込

- 予約担当が毎朝手作業で行っている入金の消込をなくし、振込済への更新を朝7時までに済ませる（S-22-001/D-01002/1・処理の目的・利用者）
- 消し込めなかった入金は、予約担当が確認できるリストにまとめる（S-22-001/D-01002/2・処理の目的・利用者）
- 銀行休業日に振り込まれた分は、翌営業日のファイルに、翌営業日の勘定日で入る（S-22-001/D-04006/2・業務カレンダー）
<!-- tazuna:design S-22-001 end -->

<!-- tazuna:design S-23-001 begin src=e69d1d51ee80（scripts/design/transcribe.py が作る。手で直さない） -->
## S-23-001 ジョブ設計書：J110振込取込

- J110 は S1 受信確認・S2 形式検査・S3 消込・S4 リスト出力・S5 退避 の5ステップ（S-23-001/D-08001/1・ジョブ一覧・ジョブネット）
<!-- tazuna:design S-23-001 end -->

<!-- tazuna:design S-24-001 begin src=3967873f43de（scripts/design/transcribe.py が作る。手で直さない） -->
## S-24-001 IF定義書：IF-11振込入金通知ファイル

- 全銀協の振込入金通知フォーマットと、取引銀行の「ファイル伝送サービス利用要領」を正とする（S-24-001/D-07013/1・相手システムの仕様書）
<!-- tazuna:design S-24-001 end -->

<!-- tazuna:design S-32-001 begin src=cd8b1b0969e6（scripts/design/transcribe.py が作る。手で直さない） -->
## S-32-001 運用設計書：運用設計書

- 運用手順書は社内の運用ポータル「ツアー予約」ページにある（S-32-001/D-16006/1・運用ドキュメントの所在）
- お客様からの問い合わせは、予約番号で操作ログと手配連携の履歴を引く（S-32-001/D-16007/1・問い合わせで見る情報）
- お客様から入金の問い合わせがあれば、予約番号で取込結果テーブルと不一致リストを引く（S-32-001/D-16007/2・問い合わせで見る情報）
<!-- tazuna:design S-32-001 end -->

<!-- tazuna:design S-34-001 begin src=c72a578a64b8（scripts/design/transcribe.py が作る。手で直さない） -->
## S-34-001 開発ガイド：開発ガイド

- 新しいユースケースは ReservationService#reserve を手本にする（S-34-001/D-18007/1・手本とするコード）
<!-- tazuna:design S-34-001 end -->

<!-- tazuna:design S-20-001 begin src=42455c351482（scripts/design/transcribe.py が作る。手で直さない） -->
## S-20-001 データモデル設計書：データモデル設計書

- TOURINFO と MEMBER はマスタ、RESERVE・TRANSFER_IMPORT・REFUND・CLAIM はトランザクション（S-20-001/D-05014/2・マスタとトランザクションの区別）
<!-- tazuna:design S-20-001 end -->

<!-- tazuna:design S-16-003 begin src=906747d566b5（scripts/design/transcribe.py が作る。手で直さない） -->
## S-16-003 テーブル設計書：REFUND

- 予約の取消で、入金額が取消料より多いときに増える（振込済の予約と、不一致の入金がある未振込の予約）。年に数千件の見込み（S-16-003/D-05011/2・データ量・増加見込み）
- トランザクション（S-16-003/D-05014/1・マスタとトランザクションの区別）
<!-- tazuna:design S-16-003 end -->

<!-- tazuna:design S-22-002 begin src=6e414b6f6ff6（scripts/design/transcribe.py が作る。手で直さない） -->
## S-22-002 処理設計書：予約取消

- お客様（会員）が自分の予約を、窓口担当がお客様から電話で受けた予約を取り消す（S-22-002/D-01002/1・処理の目的・利用者）
<!-- tazuna:design S-22-002 end -->

<!-- tazuna:design S-16-006 begin src=ffb64bb38915（scripts/design/transcribe.py が作る。手で直さない） -->
## S-16-006 テーブル設計書：CLAIM

- 予約の取消で、入金額が取消料より少ないときに増える（入金のない予約の取消を含む）。未振込の予約の取消が多いと、REFUND より多くなりうる（S-16-006/D-05011/1・データ量・増加見込み）
- トランザクション（S-16-006/D-05014/1・マスタとトランザクションの区別）
<!-- tazuna:design S-16-006 end -->
