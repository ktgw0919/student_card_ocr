# デジタル学生証 読み取り・真偽判定システム アーキテクチャ仕様書

## 1. プロジェクト概要

本プロジェクトは、デジタル学生証のスクリーンショットや「直撮りの静止画」を入力とし、QRコードによる「偽造防止・真偽判定」と、高精度OCRエンジン「YomiToku」による「テキスト・レイアウト抽出」を統合して行うバックエンドシステムです。

直撮り特有の照明反射やピンボケに耐えうる「画像補正のマルチ戦略」や、無関係なQRが写り込んだ場合・QRが存在しない場合でもシステムを停止させずにOCRを完遂する「完全なフォールバック設計（Graceful Degradation）」を実装しています。

OCRの生データ（`raw_data`）は、後処理層（`ocr/postprocess`）で文書種別ごとに構造化され、クライアントは主に `structured` フィールドを参照します。

## 2. システム構成（全体アーキテクチャ）

システムは「フロントエンド」と「バックエンド」に分離されており、バックエンド内は各処理層が独立（疎結合）し、テスト容易性を担保しています。

```
[クライアント (スマホブラウザ/アプリ等)]
       │
       │ (HTTP POST multipart: 画像ファイル)
       ▼
[Web層 (main.py)]
       │  GET /health（認証不要）
       │  POST /verify: API Key・レート制限・画像検証 → 一時ファイル → image_path
       │  lifespan: Playwright Browser を起動・共有
       ▼
[Service層 (services/student_card_service.py)]
       │  QR検証 + OCR + 構造化を統合
       ├──────────────────────────────┐
       ▼                              ▼
[QR検証層 (qr/verifier.py)]    [OCR層 (ocr/yomitoku_impl.py)]
 OpenCV + pyzbar + Playwright    YomiToku → raw_data
       │                              │
       │                              ▼
       │                    [後処理層 (ocr/postprocess)]
       │                      正規化 → ルーティング → 抽出器
       │                              │
       └──────────────┬───────────────┘
                      ▼
              JSON レスポンス (status, qr_status, message, data)
```

## 3. ディレクトリ構造

「Adapterパターン」と「抽出器プラグイン」を意識したモジュール分割です。

```
student_card_ocr/
├── .venv/                          # 仮想環境 (uvにより管理)
├── debug_output/                   # デバッグ時の可視化画像・JSON出力先（自動生成）
├── raw_data_output/                # collect_raw_data.py の出力先（.gitignore・ローカルのみ）
├── docs/
│   └── PRIVACY.md                  # 個人情報保護・Git 管理方針
├── core/
│   └── config.py                   # 環境変数や全体設定（将来用）
├── models/
│   └── schemas.py                  # Pydantic API スキーマ（VerifyResponse 等）
├── ocr/
│   ├── base.py                     # OCRエンジン抽象基底クラス (BaseOCREngine)
│   ├── yomitoku_impl.py            # YomiToku実装
│   └── postprocess/                # raw_data → structured 変換
│       ├── normalizer.py           # テキスト・段落の正規化
│       ├── router.py               # 文書種別判定と抽出器ルーティング
│       ├── pipeline.py             # process_raw_data() エントリポイント
│       └── extractors/
│           ├── base.py             # BaseExtractor インターフェース
│           ├── student_card_jp.py  # 日本の学生証
│           └── driver_license_jp.py # 日本の運転免許証（ルーティング・基本抽出）
├── qr/
│   └── verifier.py                 # QR検出と Playwright 真偽判定
├── services/
│   └── student_card_service.py     # ビジネスロジック統合層
├── tests/
│   ├── fixtures/anonymized/        # 匿名化 OCR JSON（Git 管理）
│   ├── test_images/                # test_student_card_01/02.jpg のみ Git 可
│   ├── test_verifier.py            # QR検証の統合テスト（pytest-asyncio）
│   └── postprocess/
│       └── test_postprocess.py     # 構造化抽出の回帰テスト
├── main.py                         # FastAPI エントリポイント
├── collect_raw_data.py             # フォルダ一括OCR・raw_data収集（開発用）
├── test_yomitoku_run.py            # YomiToku 単体動作確認
├── pyproject.toml
└── uv.lock
```

## 4. 技術スタック

### 4.1 パッケージ・環境管理

- **uv**: 高速なRust製のPythonパッケージマネージャー。仮想環境構築と依存関係解決を統合。

### 4.2 コアライブラリ

- **YomiToku**: 日本語文書画像解析に特化した高精度OCRエンジン。
- **opencv-python (cv2)**: 画像の最適化（リサイズ、CLAHE、適応的2値化）およびデバッグ画像の生成。
- **pyzbar**: 画像からのQRコード検出およびデータ（URL）抽出。
- **Playwright**: ヘッドレスブラウザによるJSレンダリングと、大学認証サーバー（app.omu.ac.jp）への真偽判定。

### 4.3 テスト・Webフレームワーク

- **pytest / pytest-asyncio**: 非同期テストを含む自動テスト。
- **FastAPI / uvicorn**: 非同期Web API。`POST /verify` で画像を受け付ける。

## 5. 主要なデータフロー

### 5.1 API リクエスト〜レスポンス

1. **リクエスト受信:** `main.py` が `UploadFile` を受け取り、`tempfile` でディスクに保存する。
2. **Service 呼び出し:** 一時ファイルパスを `StudentIDService.process(image_path)` に渡す。
3. **フェーズ1（QR検証）:** `qr/verifier.py` が画像前処理・QR検出を行い、正規URLなら Playwright で認証ページを判定する。
4. **フェーズ2（OCR抽出）:** QR状態に関わらず `YomiTokuEngine.extract()` を実行し `raw_data` を取得する。
5. **フェーズ3（構造化）:** `process_raw_data(raw_data)` で `structured` を生成する。
6. **レスポンス返却:** `status`, `qr_status`, `message`, `data`（`engine`, `raw_data`, `structured`）を返す。

### 5.2 QR検証の3状態

| 状態 | 意味 |
|------|------|
| `VALID` | 正規QRで認証成功 |
| `NOT_FOUND` | QR未検出 |
| `UNVERIFIABLE` | QRはあるが無効・期限切れ・対象外 |

認証成功文言は、大阪市立大学・大阪府立大学・大阪公立大学の表記に対応しています。

### 5.3 OCR後処理（構造化）パイプライン

1. **正規化 (`normalizer.py`):** `paragraphs` / `figures` 内テキストを統一（改行・空白・ラベル揺れ）。
2. **ルーティング (`router.py`):** 各抽出器の `can_handle()` スコアを比較し、閾値以上の最適抽出器を選択。未満なら `document_type: unknown`。
3. **抽出 (`extractors/*.py`):** 種別ごとにフィールドを抽出（学籍番号・氏名・有効期限など）。

拡張時は `ocr/postprocess/extractors/` に新しい抽出器を追加し、`router.py` のリストに登録する。

## 6. Playwright のライフサイクル管理

`main.py` の `lifespan` で、アプリ起動時に **Browser を1回だけ** 起動し、`app.state` 経由で `QRVerifier(browser=...)` に注入します。

- リクエストごと: `browser.new_page()` のみ（起動コストを削減）
- 終了時: `browser.close()` / `playwright.stop()`
- `QRVerifier` は Browser 未注入時、フォールバックとして都度起動も可能（CLI・テスト用）

## 7. API レスポンス構造

`POST /verify` は `response_model=VerifyResponse`（`models/schemas.py`）。`status` / `qr_status` / `FieldStatus` は Enum で OpenAPI に反映される。

### 7.1 `data` フィールド

```json
{
  "engine": "YomiToku",
  "raw_data": { "paragraphs": [...], "words": [...], "figures": [...] },
  "structured": {
    "document_type": "student_card",
    "schema_id": "student_card_jp",
    "issuer_hint": "サンプル大学",
    "extractor_name": "StudentCardJpExtractor",
    "routing_score": 1.0,
    "confidence": 1.0,
    "fields": {
      "student_id": {
        "value": "X00XX000",
        "normalized_value": "X00XX000",
        "status": "found",
        "confidence": 0.9,
        "source_text": "学籍番号 X00XX000"
      },
      "name": { "...": "..." },
      "expiry_date": { "normalized_value": "2027-03-31", "...": "..." }
    },
    "warnings": []
  }
}
```

- クライアントは **`structured` を主参照** とする。
- `raw_data` は **デフォルト非返却**（`ALLOW_INCLUDE_RAW=true` かつ `?include_raw=true` でオプトイン）。
- `structured.fields.*.source_text` もデフォルト非返却（`?include_source_text=true` でオプトイン）。

## 8. 実装上の重要ポイント

- **非同期スレッド処理:** OpenCV・pyzbar・YomiToku推論は `asyncio.to_thread()` でオフロード。Playwright は async API を使用。
- **UploadFile と image_path のブリッジ:** 下位層は `cv2.imread(path)` 前提のため、Web層で一時ファイル化してから Service に渡す。
- **直撮りQR検出:** 複数の2値化・コントラスト戦略を順に試行するマルチ戦略。
- **構造化の拡張性:** 抽出器プラグイン + ルーター方式により、他大学・他身分証を追加しやすい。
- **テスト戦略:**
  - `tests/test_verifier.py`: 実画像・実通信（`@pytest.mark.asyncio`）
  - `tests/postprocess/test_postprocess.py`: 匿名化 fixture（`tests/fixtures/anonymized/`）による回帰テスト
  - `tests/test_verifier.py`: `test_student_card_01.jpg` / `test_student_card_02.jpg`（Git 許可画像）
- **開発用ツール:** `collect_raw_data.py` でフォルダ内画像から `raw_data` を一括収集可能。

## 9. 今後の拡張方針

- **他大学・他身分証向け抽出器の追加**
- **CORS 設定**（フロントエンド連携時）
- **環境変数化** (`core/config.py`): デバッグモード、認証URL、ルーティング閾値など
- **`raw_data` の本番非返却オプション**（帯域・PII観点）
