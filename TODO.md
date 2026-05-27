# プロジェクト TODO および進捗管理

## ✅ 完了済みの実装 (Completed)

### 1. OCRエンジン層 (`ocr/yomitoku_impl.py`)

- [x] YomiTokuを利用した高精度なテキスト・レイアウト抽出。
- [x] `asyncio.to_thread` による同期処理の非同期オフロード（ブロッキング回避）。
- [x] ルビ（ふりがな）の除外設定 (`ignore_ruby=True`) によるノイズ低減。
- [x] `tempfile` を利用した安全なJSONデータのメモリ展開。
- [x] デバッグモード時のバウンディングボックス可視化画像出力。
- [x] `BaseOCREngine` 抽象基底クラスへの準拠（タイポ修正済み）。

### 2. QRコード検証層 (`qr/verifier.py`)

- [x] `pyzbar` を用いたQRコードからのURL抽出。
- [x] 直撮り画像に耐える前処理マルチ戦略（リサイズ、CLAHE、適応的2値化）。
- [x] Playwright による大学認証サーバー（app.omu.ac.jp）の真偽判定（非同期化）。
- [x] 3つの状態 (`VALID`, `NOT_FOUND`, `UNVERIFIABLE`) を返す Enum 設計。
- [x] 大阪市立大学・大阪府立大学・大阪公立大学の認証成功文言に対応。
- [x] FastAPI lifespan による Browser 共有（リクエストごとの `chromium.launch()` を廃止）。

### 3. ビジネスロジック層 (`services/student_card_service.py`)

- [x] QR検証とOCR抽出を統合する司令塔の構築。
- [x] QRコードの状態に関わらず、必ずOCRを実行するフォールバック設計。
- [x] OCR後処理の統合（`structured` フィールドの付与）。
- [x] `QRVerifier` / `YomiTokuEngine` の DI 対応。

### 4. Web API層 (`main.py`)

- [x] FastAPI アプリケーションの初期化。
- [x] `POST /verify` エンドポイント（`UploadFile` 受信）。
- [x] 一時ファイル経由で Service 層へ `image_path` を渡すブリッジ処理。
- [x] lifespan による Playwright Browser の起動・終了管理。

### 5. OCR後処理・構造化層 (`ocr/postprocess/`)

- [x] `raw_data` の正規化（`normalizer.py`）。
- [x] 文書種別ルーティング（`router.py`）。
- [x] 抽出器プラグイン設計（`extractors/base.py`）。
- [x] 日本の学生証抽出器（学籍番号・氏名・有効期限）。
- [x] 日本の運転免許証ルーティング（`driver_license_jp.py`）。
- [x] 収集サンプル（学生証4枚・免許証1枚）に対する回帰テスト。

### 6. テスト・開発ツール

- [x] `tests/test_verifier.py` の非同期化（`pytest-asyncio`）。
- [x] `tests/postprocess/test_postprocess.py` による構造化テスト。
- [x] `collect_raw_data.py` によるフォルダ一括 `raw_data` 収集。
- [x] `ARCHITECTURE.md` によるアーキテクチャ文書の整備。

### 7. 個人情報保護（GitHub 公開向け）

- [x] `.gitignore` 拡充（`raw_data_output/`, `debug_output/`, `sample_data/`, 画像など）。
- [x] 匿名化 OCR fixture（`tests/fixtures/anonymized/`）への移行。
- [x] テスト期待値の架空データ化（`X00XX000`, `山田 太郎`）。
- [x] `tests/test_verifier.py` を `test_student_card_01/02.jpg` ベースに変更。
- [x] ローカル任意画像は `tests/test_images/local/`（Git 除外）。
- [x] `docs/PRIVACY.md` による運用方針の明文化。

---

## 🚧 次に実装すべき残タスク (To Do / Next Steps)

### 1. API スキーマの厳格化 (`models/schemas.py`)

- [x] Pydantic によるレスポンス型定義（`VerifyResponse` 等）。
- [x] FastAPI の `response_model` 適用（`response_model_exclude_none=True`）。
- [x] `structured.fields` の型安全なアクセス（`ExtractedFieldOut` / `FieldStatus`）。

### 2. Web API の運用強化 (`main.py`)

- [x] CORS 設定（`CORS_ORIGINS` カンマ区切り）。
- [x] リクエストサイズ制限（`MAX_UPLOAD_BYTES`）・画像形式バリデーション（JPEG/PNG/WebP、`core/upload.py`）。
- [x] ヘルスチェック（`GET /health`）。
- [x] API Key 認証（`REQUIRE_API_KEY` / `X-API-Key`）。
- [x] レート制限（`RATE_LIMIT_PER_MINUTE`、インメモリ）。

### 3. OCR後処理の拡張

- [ ] 他大学の学生証向け抽出器の追加（表記・学籍番号フォーマットの違い）。
- [ ] 運転免許証の氏名・有効期限抽出精度の向上。
- [ ] 在留カード・マイナンバーカード等の将来対応。
- [ ] ルーティング閾値・ラベル辞書の設定ファイル化。

### 4. 環境変数・設定管理 (`core/config.py`)

- [x] Phase 1: `pydantic-settings`（`debug_mode`, `allow_include_raw`, `include_*_default`, `max_upload_bytes`）。
- [ ] 認証URL、Playwright タイムアウト等の追加 `.env` 化。

### 5. データセット・評価

- [ ] 他大学向け匿名 fixture の追加（ローカル実データから手動匿名化して fixture 化）。
- [ ] 抽出精度メトリクス（フィールドごとの正解率）の自動集計。

### 6. セキュリティ・運用

- [ ] pre-commit + `gitleaks` / `detect-secrets` の導入。
- [ ] 過去コミットに PII が含まれていた場合の履歴清掃（`git filter-repo`）。

---

## 🐛 既知の課題・検討事項 (Known Issues / Backlog)

- **`raw_data` の本番返却**（Phase 1 対応済み）:
  デフォルト非返却。`ALLOW_INCLUDE_RAW=true` の環境でのみ `?include_raw=true` が有効。
- **運転免許証の抽出精度**:
  ルーティングは可能だが、氏名・有効期限の抽出ルールは MVP 段階。学生証ほど精度検証されていない。
- **学生証の大学バリエーション**:
  回帰テストは匿名 fixture が中心。実カードでの検証はローカルのみ。他大学フォーマットは未検証。
- **pre-commit による漏洩検知**:
  `gitleaks` 等の導入は未実施。公開前に検討する。
- **極端な直撮り画像の限界**:
  QRが極小・ピンボケの場合は `NOT_FOUND` となる。フロントエンド側の撮影ガイドによる運用カバーが必要。
