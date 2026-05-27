"""FastAPI 依存性（認証・レート制限）。"""

from fastapi import Header, HTTPException, Request

from core.config import Settings
from core.rate_limit import RateLimiter


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


async def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    settings: Settings = request.app.state.settings
    if not settings.require_api_key:
        return
    if not settings.api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="認証に失敗しました。")


async def enforce_rate_limit(request: Request) -> None:
    settings: Settings = request.app.state.settings
    limiter: RateLimiter = request.app.state.rate_limiter

    if settings.rate_limit_per_minute <= 0:
        return

    client_key = request.headers.get("X-API-Key") or (
        request.client.host if request.client else "unknown"
    )
    limiter.check(client_key)
