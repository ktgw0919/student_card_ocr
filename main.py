import asyncio
import logging
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

_WEB_DIR = Path(__file__).resolve().parent / "web"

from core.config import Settings, get_settings
from core.deps import enforce_rate_limit, verify_api_key
from core.rate_limit import RateLimiter
from core.upload import validate_image_bytes
from models.schemas import HealthResponse, VerifyResponse
from ocr.yomitoku_impl import YomiTokuEngine
from qr.verifier import QRVerifier
from services.response_builder import build_verify_response, resolve_include_flags
from services.student_card_service import StudentIDService

logger = logging.getLogger(__name__)

_GENERIC_ERROR_DETAIL = "画像の処理に失敗しました。しばらく経ってから再度お試しください。"


def create_app(settings: Settings | None = None) -> FastAPI:
    """テスト用: 設定を注入してアプリを構築する。"""
    resolved = settings or get_settings()
    resolved.validate_auth_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved
        app.state.rate_limiter = RateLimiter(
            max_calls=resolved.rate_limit_per_minute,
            window_seconds=60,
        )

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)

        app.state.service = StudentIDService(
            qr_verifier=QRVerifier(browser=browser, debug_mode=resolved.debug_mode),
            ocr_engine=YomiTokuEngine(debug_mode=resolved.debug_mode),
        )
        try:
            yield
        finally:
            await browser.close()
            await playwright.stop()

    application = FastAPI(title="Student Card OCR API", lifespan=lifespan)

    cors_origins = resolved.cors_origin_list()
    if cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    if _WEB_DIR.is_dir():

        @application.get("/", include_in_schema=False)
        async def web_index() -> FileResponse:
            return FileResponse(_WEB_DIR / "index.html")

        application.mount(
            "/web",
            StaticFiles(directory=_WEB_DIR),
            name="web",
        )

    @application.post(
        "/verify",
        response_model=VerifyResponse,
        response_model_exclude_none=True,
        dependencies=[Depends(verify_api_key), Depends(enforce_rate_limit)],
    )
    async def verify_student_card(
        file: UploadFile = File(...),
        include_raw: bool | None = Query(
            default=None,
            description="YomiToku raw_data を返す（ALLOW_INCLUDE_RAW=true の環境のみ）",
        ),
        include_source_text: bool | None = Query(
            default=None,
            description="structured.fields.*.source_text を返す",
        ),
    ) -> VerifyResponse:
        app_settings: Settings = application.state.settings
        include_raw_flag, include_source_flag, forbid = resolve_include_flags(
            app_settings,
            include_raw=include_raw,
            include_source_text=include_source_text,
        )
        if forbid:
            raise HTTPException(status_code=403, detail=forbid)

        tmp_path: Path | None = None

        try:
            file_bytes = await file.read()
            suffix = validate_image_bytes(
                file_bytes, max_bytes=app_settings.max_upload_bytes
            )

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                tmp_path = Path(tmp.name)

            raw_response = await application.state.service.process(str(tmp_path))
            return build_verify_response(
                raw_response,
                include_raw=include_raw_flag,
                include_source_text=include_source_flag,
                debug_mode=app_settings.debug_mode,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("verify_student_card failed")
            detail = _GENERIC_ERROR_DETAIL
            if app_settings.debug_mode:
                detail = f"{_GENERIC_ERROR_DETAIL} ({exc})"
            raise HTTPException(status_code=500, detail=detail)
        finally:
            await file.close()
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink()

    return application


app = create_app()
