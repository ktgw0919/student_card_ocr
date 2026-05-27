# テスト用画像

## Git 管理対象（匿名化サンプルのみ）

次の2ファイルのみコミット可能です（`.gitignore` で明示許可）。

- `test_student_card_01.jpg`
- `test_student_card_02.jpg`

学生証の実画像が必要なテストでは、上記ファイルをこのディレクトリに配置してください。

## Git 管理禁止

- 実名・実学籍番号・QR付き本物の学生証画像
- `qr_valid.jpg`, `no_qr.jpg` などローカル検証用画像（必要なら各自で配置し、コミットしない）

ローカル専用画像は `tests/test_images/local/` など別フォルダに置くことを推奨します（`local/` は `.gitignore` で除外済み）。
