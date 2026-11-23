# アーキテクチャ

管理者は案件リーダー。境界は文章ではなく `src/test/java/com/example/architecture/ArchitectureTest.java`（ArchUnit）で強制する。

## レイヤー

| レイヤー | パッケージ | 置くもの |
| --- | --- | --- |
| domain | `com.example.domain` | 業務ルール、値オブジェクト（`Money`）、エンティティ（`Tour`・`Reservation`）、業務ルール（`CancellationPolicy`）、リポジトリの interface |
| application | `com.example.application` | ユースケース（`ReservationService`） |
| infrastructure | `com.example.infrastructure` | DB・外部APIなど入出力の実装（見本はインメモリ） |

domain は入出力（`java.sql`、`java.io`、`java.net`）に依存しない（ARCH-002）。

## 依存方向

```
infrastructure ──▶ application ──▶ domain
       └──────────────────────────▶ domain
```

- domain はどの層にも依存しない（ARCH-001）。
- 永続化が必要なら、domain に interface を置き、実装を infrastructure に置く（依存性の逆転）。

## 案件での変更

- パッケージ名を案件のものに変えたら、`ArchitectureTest` のパッケージ指定も合わせて変える。
- レイヤーを増やす（presentation など）ときは、この文書と `ArchitectureTest` を同じPRで変える。
