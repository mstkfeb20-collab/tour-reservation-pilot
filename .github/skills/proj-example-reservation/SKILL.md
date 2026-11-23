---
name: proj-example-reservation
description: 【見本】ツアー予約（予約・取消・取消料）に関わる機能を実装・レビューするときに使う。案件では、このスキルを自分のドメインに合わせて書き換えるか削除する。
---

# ツアー予約ドメインの進め方（見本）

> これは proj- スキルの書き方の見本です。案件では削除するか、自分のドメインのスキルに置き換えてください。

進め方の基本は `base-task-workflow` に従う。ここにはツアー予約に特有のことだけを書く。業務ルールそのものは書かず、`docs/domain/` と `docs/requirements/reservation.md` を参照する。

## ツアー予約で特に確認すること

- 金額は必ず `com.example.domain.Money` を使う（INV-001）。取消料の端数は `percent()` で切り捨て、返金は `minusOrZero()` で0円未満にしない（INV-004）。
- 振込状況は `Reservation` の `markPaid()`・`cancel()` でだけ変える（INV-002）。新しい状態を追加するときは、遷移図を `docs/domain/feature-map.md` に先に書き、承認を得てから実装する。
- 残席数は `Tour` の `reserveSeats()`・`releaseSeats()` でだけ変え、予約・取消の登録と同じ処理の中で行う（INV-003）。
- 日付の境界（7日前・前日・21日前・8日前・2日前）は「出発日 − 今日」の日数で判定する。今日の日付は引数で受け取り、テストでは境界の前後を両方確かめる。
- 区分値（0・1・9）は既存システムと同じ値を使う。値を変える要件が来たら、既存データの移行が要るので、実装前にレビュアーに確認する。

## 参照先

- 要件: `docs/requirements/reservation.md`（REQ-001〜003）
- 業務ルール: `docs/domain/invariants.md`（INV-001〜004）
- 用語: `docs/domain/glossary.md`（予約、振込状況、取消料、返金額）
- 機能一覧と状態遷移: `docs/domain/feature-map.md`
