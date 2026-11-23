# 背景知識

> ID 設計から転記した、判断の材料になる事実。守らせるルールではない。

<!-- tazuna:design S-12-001 begin src=f3931a0d4ed6（scripts/design/transcribe.py が作る。手で直さない） -->
## S-12-001 画面共通設計書：画面共通設計書

- 画面・メッセージ・帳票では「取消」で統一し、「キャンセル」は使わない（S-12-001-003・文言・ラベル）
- 「振込済」は「入金済」と書かない。銀行振込以外の入金手段がないため（S-12-001-004・文言・ラベル）
<!-- tazuna:design S-12-001 end -->

<!-- tazuna:design S-16-001 begin src=44ecc495273a（scripts/design/transcribe.py が作る。手で直さない） -->
## S-16-001 テーブル定義書：RESERVE

- 予約は年間約30万件増える。照会は直近2年分が対象（S-16-001-028・データ量・増加見込み）
- RESERVE は年間約30万件増える。販売開始日は1時間に最大3千件登録される（S-16-001-029・データ量・増加見込み）
<!-- tazuna:design S-16-001 end -->

<!-- tazuna:design S-16-002 begin src=e14105585e86（scripts/design/transcribe.py が作る。手で直さない） -->
## S-16-002 テーブル定義書：TRANSFER_IMPORT

- 振込明細は平常1日300件、繁忙期は最大3千件（S-16-002-009・データ量・増加見込み）
<!-- tazuna:design S-16-002 end -->

<!-- tazuna:design S-17-001 begin src=716e6960296a（scripts/design/transcribe.py が作る。手で直さない） -->
## S-17-001 共通部品設計書：共通部品設計書

- 共通部品は Money（金額）・BusinessCalendar（営業日）・CodeValue（区分値）（S-17-001-004・共通部品の一覧）
<!-- tazuna:design S-17-001 end -->

<!-- tazuna:design S-18-001 begin src=3aff109e7ad3（scripts/design/transcribe.py が作る。手で直さない） -->
## S-18-001 バッチ共通設計書：バッチ共通設計書

- /TOUR/NIGHTLY: J110 振込取込 → J120 残席突合 → J310 予約一覧表（S-18-001-001・ジョブ一覧・ジョブネット）
<!-- tazuna:design S-18-001 end -->

<!-- tazuna:design S-19-001 begin src=1c915957a48e（scripts/design/transcribe.py が作る。手で直さない） -->
## S-19-001 非機能設計書：非機能設計書

- 性能は本番相当（ツアー5千件・予約60万件）のデータで測る（S-19-001-002・性能測定の条件）
<!-- tazuna:design S-19-001 end -->

<!-- tazuna:design S-22-001 begin src=2ce5e60b418c（scripts/design/transcribe.py が作る。手で直さない） -->
## S-22-001 処理設計書：振込データ取込

- 予約担当が毎朝手作業で行っている入金の消込をなくし、振込済への更新を朝7時までに済ませる（S-22-001-001・処理の目的・利用者）
- 消し込めなかった入金は、予約担当が確認できるリストにまとめる（S-22-001-002・処理の目的・利用者）
- 銀行休業日に振り込まれた分は、翌営業日のファイルに、翌営業日の勘定日で入る（S-22-001-025・業務カレンダー）
<!-- tazuna:design S-22-001 end -->

<!-- tazuna:design S-23-001 begin src=66cfc45ce1d9（scripts/design/transcribe.py が作る。手で直さない） -->
## S-23-001 ジョブ設計書：J110振込取込

- J110 は S1 受信確認・S2 形式検査・S3 消込・S4 リスト出力・S5 退避 の5ステップ（S-23-001-001・ジョブ一覧・ジョブネット）
<!-- tazuna:design S-23-001 end -->

<!-- tazuna:design S-24-001 begin src=e381ebedec1e（scripts/design/transcribe.py が作る。手で直さない） -->
## S-24-001 IF定義書：IF-11振込入金通知ファイル

- 全銀協の振込入金通知フォーマットと、取引銀行の「ファイル伝送サービス利用要領」を正とする（S-24-001-028・相手システムの仕様書）
<!-- tazuna:design S-24-001 end -->

<!-- tazuna:design S-32-001 begin src=a9003f8b2269（scripts/design/transcribe.py が作る。手で直さない） -->
## S-32-001 運用設計書：運用設計書

- 運用手順書は社内の運用ポータル「ツアー予約」ページにある（S-32-001-010・運用ドキュメントの所在）
- お客様からの問い合わせは、予約番号で操作ログと手配連携の履歴を引く（S-32-001-011・問い合わせで見る情報）
- お客様から入金の問い合わせがあれば、予約番号で取込結果テーブルと不一致リストを引く（S-32-001-012・問い合わせで見る情報）
<!-- tazuna:design S-32-001 end -->

<!-- tazuna:design S-34-001 begin src=cff068e5465b（scripts/design/transcribe.py が作る。手で直さない） -->
## S-34-001 開発ガイド：開発ガイド

- 新しいユースケースは ReservationService#reserve を手本にする（S-34-001-007・手本とするコード）
<!-- tazuna:design S-34-001 end -->
