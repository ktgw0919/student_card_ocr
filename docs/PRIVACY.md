# 個人情報保護と Git 管理方針

## 原則

- **実カードの OCR 結果・実画像・QR付き本物画像は Git に含めない**
- リポジトリに置くテストデータは **匿名化・架空データのみ**
- ローカル開発で収集した `raw_data` は `raw_data_output/` に出力し、`.gitignore` で除外する

## Git 管理対象

| 種別 | 例 |
|------|-----|
| 匿名 OCR JSON | `tests/fixtures/anonymized/*.raw.json` |
| 許可されたテスト画像 | `tests/test_images/test_student_card_01.jpg`, `test_student_card_02.jpg` |
| ソースコード・ドキュメント（実名・実番号なし） | `*.py`, `ARCHITECTURE.md` 等 |

## Git 管理禁止（`.gitignore`）

- `raw_data_output/` — `collect_raw_data.py` の出力
- `debug_output/` — デバッグ可視化・JSON
- `sample_data/` — ローカル実画像
- `tests/test_images/local/` — 各自の検証用画像
- 上記以外の `*.jpg` 等（許可2ファイルを除く）

## ローカル開発

```bash
# raw_data 収集（出力は Git 対象外）
python collect_raw_data.py --input-dir ./local_images --output-dir ./raw_data_output

# 任意の QR 統合テスト用画像
# tests/test_images/local/qr_valid.jpg などに配置（コミットしない）
```

## 公開前チェック

1. `git status` に `raw_data_output/`, `debug_output/`, 実画像が含まれていないか
2. テスト・ドキュメントに実名・学籍番号・住所が残っていないか
3. 過去コミットに PII が含まれていた場合は `git filter-repo` 等で履歴清掃

## API 返却（Phase 1 実装済み）

- 本番デフォルト: `raw_data` は **返却しない**（`ALLOW_INCLUDE_RAW=false`）
- `structured.fields.*.source_text` もデフォルト非返却
- 開発時のみ `.env` で `ALLOW_INCLUDE_RAW=true` とし、`POST /verify?include_raw=true` で取得可能
- OCR 失敗時の `data.error` は本番では汎用メッセージのみ（詳細はサーバログ）

## 推奨（将来）

- pre-commit で `gitleaks` / `detect-secrets` を実行
