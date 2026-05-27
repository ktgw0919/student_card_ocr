# Student Card OCR

デジタル学生証の QR 真偽判定と OCR 構造化抽出を行うバックエンドです。

## ドキュメント

- [アーキテクチャ](ARCHITECTURE.md)
- [初回セットアップ / 別端末利用](docs/SETUP.md)
- [個人情報保護・Git 管理方針](docs/PRIVACY.md)
- [進捗・TODO](TODO.md)

## テスト

```bash
uv run pytest tests/postprocess/ -v
uv run pytest tests/test_api_response.py tests/test_api_ops.py -v
uv run pytest tests/test_verifier.py -v
```

## 起動（API + 撮影 UI）

事前に `docs/SETUP.md` の「初回セットアップ」を実施してください。

```powershell
# Windows: --reload は Playwright と相性が悪いため付けない
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

| URL                          | 用途                       |
| ---------------------------- | -------------------------- |
| http://127.0.0.1:8000/       | 撮影・検証 UI（フェーズ1） |
| http://127.0.0.1:8000/docs   | OpenAPI                    |
| http://127.0.0.1:8000/health | 死活監視                   |

**スマホから使う場合:** PC と同一 Wi‑Fi にし、PC の LAN IP で `http://<IP>:8000/` を開く。iPhone でカメラが使えない場合は HTTPS トンネル（ngrok 等）を検討。

開発用 `.env` の例: `RATE_LIMIT_PER_MINUTE=0`, `REQUIRE_API_KEY=false`

## API

- `GET /health` — 死活監視（認証不要）
- `POST /verify` — 学生証検証（任意: `X-API-Key`、`?include_raw`）
- レスポンス型: `VerifyResponse`（OpenAPI: `/docs`）
- 設定: `.env.example` を参照

本番の推奨例: `REQUIRE_API_KEY=true`, `ALLOW_INCLUDE_RAW=false`, `CORS_ORIGINS` にフロントのオリジンのみ指定。

学生証画像テストには `tests/test_images/test_student_card_01.jpg` と `test_student_card_02.jpg` を配置してください。

## 開発用（Git 管理外）

```bash
python collect_raw_data.py --input-dir ./local_images --output-dir ./raw_data_output
```

出力は個人情報を含むため **コミットしない** でください。
