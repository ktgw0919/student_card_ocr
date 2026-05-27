from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定（環境変数 / .env で上書き可能）。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug_mode: bool = False

    # 本番では False: ?include_raw=true を拒否
    allow_include_raw: bool = False
    include_raw_default: bool = False

    include_source_text_default: bool = False

    max_upload_bytes: int = 10 * 1024 * 1024

    # Phase 3: CORS（カンマ区切り。空なら CORS ミドルウェアを登録しない）
    cors_origins: str = ""

    # Phase 3: API Key（require_api_key=true のとき必須）
    api_key: str | None = None
    require_api_key: bool = False

    # Phase 3: レート制限（0 で無効）
    rate_limit_per_minute: int = 30

    @field_validator("rate_limit_per_minute")
    @classmethod
    def _non_negative_rate_limit(cls, value: int) -> int:
        if value < 0:
            raise ValueError("rate_limit_per_minute must be >= 0")
        return value

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_auth_config(self) -> None:
        if self.require_api_key and not self.api_key:
            raise RuntimeError(
                "REQUIRE_API_KEY=true ですが API_KEY が設定されていません。"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
