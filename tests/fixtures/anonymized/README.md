# 匿名化 OCR フィクスチャ

このディレクトリの JSON は **架空の個人情報** のみを含み、Git 管理対象です。

- 実カードの `raw_data` は `raw_data_output/` に出力し、**コミットしない**こと（`.gitignore` 済み）。
- ローカルで `collect_raw_data.py` を実行した結果をテストに使う場合も、リポジトリへ追加しないこと。

## ファイル

| ファイル | 用途 |
|----------|------|
| `test_student_card_01.raw.json` | 標準レイアウトの学生証 OCR 結果 |
| `test_student_card_02.raw.json` | 氏名ラベル分離レイアウト |
| `driver_license_anonymized.raw.json` | 免許証ルーティング確認 |
| `expected.json` | 学生証抽出の期待値 |
