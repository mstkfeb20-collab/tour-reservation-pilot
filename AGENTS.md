# ツアー予約（tazuna パイロット）

<!-- 案件では [ ] の部分を書き換える。60行以内に保つ（scripts/lint/common/agents-md-size.sh） -->

## 原則
1. 設計前に `docs/domain/invariants.md` を読み、業務の不変条件を破らない。
2. 完了条件は `docs/requirements/` の要件ID（REQ-xxx）で判断する。
3. 提出前に Lint とテストを通す。テストを消したり止めたりして通さない。
4. 既存コードと同じ書き方を優先する。用語は `docs/domain/glossary.md` に合わせる。
5. PRには実行したコマンドと結果を証拠として書く。要約だけで済ませない。
6. テスト仕様の行から作ったテストには、その行IDを `@Tag("S-26-xxx/D-xxxxx/n")` で付ける。作業一覧・テスト仕様の行のうち対応しなかったものは、PR の本文に「未対応: 行ID（理由）」の行で書く。

## コマンド
- Lint: `scripts/lint/run-all.sh`
- ビルドとテスト: `mvn -B verify`
- ID 設計（人が実行する）: `python3 scripts/design/id_design.py list|scaffold|progress|export`、転記 `python3 scripts/design/transcribe.py`

## 参照先
| 知りたいこと | 場所 |
| --- | --- |
| 次に何をするか（人への案内） | `.github/skills/base-navigator/`（`python3 scripts/report/next.py`） |
| 作業の進め方 | `.github/skills/base-task-workflow/` |
| テストの作り方 | `.github/skills/base-test-design/` |
| 既存の設計書から業務ルールを抽出 | `.github/skills/base-spec-extraction/` |
| ID 設計書の置き場所と属性の例外を確認 | `.github/skills/base-design-check/` |
| ID 設計書のレビュー（食い違い・未定義・抜け） | `.github/skills/base-design-review/`（`python3 scripts/design/review_pack.py`） |
| 業務ルール・用語・機能一覧 | `docs/domain/` |
| レイヤーと依存方向 | `docs/architecture.md` |
| 命名・作法 | `docs/conventions.md` |
| テーブル・列の意味と制約 | `db/schema/*.sql`（DDL が正。区分値の意味は列の説明が指す設計書の行） |

## 編集できないファイル
`docs/requirements/`、`docs/domain/invariants.md`、`base-*` スキル、共通Lint、hooks、CI は hooks で保護されている。変更が必要なときはPRの説明に変更案を書く。
