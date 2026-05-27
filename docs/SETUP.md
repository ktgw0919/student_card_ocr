# 初回セットアップ / 別端末利用手順

このプロジェクトは `uv` を使って Python 依存を管理し、OCR と QR 真偽判定に `opencv-python` / `pyzbar` / `yomitoku` / `playwright` を利用します。

以下は **あなたが別の端末（別PC含む）でプロジェクトを利用する**ための手順です。

---

## 前提（必須）

1. Python: **3.12+**
2. `git` が使えること
3. `uv` がインストール済みであること（このプロジェクトは `uv.lock` を使います）

---

## 初回セットアップ（同じ端末で 1 回だけ）

### 1. リポジトリをクローン

```powershell
git clone https://github.com/<user>/<repo>.git
cd <repo>
```

### 2. 依存関係の同期（仮想環境の作成含む）

```powershell
uv sync
```

### 3. Playwright の Chromium をインストール（初回のみ）

```powershell
uv run playwright install chromium
```

> `main.py` は起動時に Playwright Chromium を起動します。ここが未実施だと、起動や `/verify` が失敗しやすくなります。

### 4. `.env` を作成（秘密/設定は各端末で個別に）

`.env` はリポジトリに含めない前提です。まずテンプレから作ります。

```powershell
copy .env.example .env
```

最小例として、ローカル開発だけ認証を無効にするなら以下のようにしてください。

```ini
REQUIRE_API_KEY=false
RATE_LIMIT_PER_MINUTE=0
```

別端末でフロントエンド連携をする場合は `CORS_ORIGINS` も必要です。

```ini
# カンマ区切り。空なら CORS 無効
CORS_ORIGINS=http://localhost:3000
```

### 5. サーバ起動

```powershell
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

起動後：

- UI: `http://127.0.0.1:8000/`
- OpenAPI: `http://127.0.0.1:8000/docs`
- 死活: `http://127.0.0.1:8000/health`

スマホから使う場合は、同一 Wi-Fi 上で PC の LAN IP に対して `http://<IP>:8000/` を開きます。

---

## 別端末（別PC）で使うとき

別端末では「初回セットアップ」の 2〜4 を再実施するのが基本です。

1. `git clone` または `git pull`
2. `uv sync`
3. `uv run playwright install chromium`（初回のみ）
4. `copy .env.example .env` → `.env` の内容を端末に合わせる
5. `uv run uvicorn main:app --host 0.0.0.0 --port 8000`

---

## テスト

### 1. 構造化後処理（おすすめ：軽い）

```powershell
uv run pytest tests/postprocess/ -v
```

### 2. API のレスポンス/挙動（サービスをモック）

```powershell
uv run pytest tests/test_api_response.py tests/test_api_ops.py -v
```

### 3. QR 真偽判定テスト（実画像が必要）

```powershell
uv run pytest tests/test_verifier.py -v
```

`tests/test_images/test_student_card_01.jpg` / `test_student_card_02.jpg` が手元に無い場合は、テストは `skip` されます。

---

## うまく動かない場合の最短確認

1. Playwright が未インストールではないか
   - `uv run playwright install chromium` を再実行
2. `.env` が無い/壊れていないか
   - `copy .env.example .env` をやり直し
3. サーバ起動はできるか
   - `GET /health` が 200 になるか

