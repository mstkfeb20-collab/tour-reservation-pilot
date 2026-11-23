# 業務の不変条件

どんな変更でも破ってはいけない業務ルール。管理者は社員（CODEOWNERS: business-team）。エージェントは編集できない（hooks で保護）。

各条件には「防ぐ層」と「担保」を書く（`scripts/lint/common/invariant-coverage.sh` が検査する）。

- 防ぐ層: `設計`（型・APIで書けなくする）／`Lint`／`テスト`／`実行検証`／`文章` のどれか
- 担保: その層で守っている仕組みのパス（`文章` 以外は必須、空白区切りで複数可）

`文章` のままの条件は、月次の見直しで上の層に移せないか検討する。

> 以下は見本です（題材はツアー予約）。案件では自分の不変条件に置き換えてください。

## INV-001 金額は double / float で扱わない
- 防ぐ層: 設計
- 担保: src/main/java/com/example/domain/Money.java scripts/lint/domain/java-money-no-float.sh
- 理由: 浮動小数点の丸め誤差で、取消料や返金額が1円ずれることがある。
- 補足: 金額は `Money` 型で受け渡す。Lint は `Money` を使わずに書かれた箇所を検出する。

## INV-002 振込状況は決められた順にしか進まず、取消は戻らない
- 防ぐ層: 設計
- 担保: src/main/java/com/example/domain/Reservation.java src/test/java/com/example/domain/ReservationTest.java
- 理由: 取消した予約が振込済に戻ると、返金と入金の記録が矛盾し、残席数も二重に戻る。
- 補足: 振込状況を直接書き換えるセッターを作らず、遷移は `markPaid()`・`cancel()` だけで行う。

## INV-003 残席数はマイナスにならない
- 防ぐ層: 設計
- 担保: src/main/java/com/example/domain/Tour.java src/test/java/com/example/application/ReservationServiceTest.java
- 理由: 残席を超えて予約を受けると、席のないお客様が出る。
- 補足: 残席数は `Tour#reserveSeats`・`releaseSeats` でだけ変える。案件で DB に置くときは、CHECK 制約か更新条件（残席数 >= 人数）でも守る。

## INV-004 返金額は0円を下回らない
- 防ぐ層: 設計
- 担保: src/main/java/com/example/domain/Money.java src/main/java/com/example/domain/CancellationPolicy.java
- 理由: マイナスの返金はお客様への請求になり、取消の手続きでは扱えない。
- 補足: `Money` はマイナスの値を持てない。差し引きは `minusOrZero` を使う。
