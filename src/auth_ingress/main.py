from __future__ import annotations

import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from auth_ingress.repositories.schema import create_schema
from auth_ingress.services.downstream_service import close_clients
from auth_ingress.services.proxy_websocket_service import close_websockets
from auth_ingress.web.routes import admin_audit, admin_groups, admin_services, admin_users, auth, health, password_reset, portal, services
from auth_ingress.web.routes.proxy import ProxyDispatchMiddleware
from auth_ingress.web.web import WEB_ROOT, template

logger = logging.getLogger("auth_portal")


class RedactingJsonFormatter(logging.Formatter):
    blocked = {"password", "authorization", "cookie", "session", "secret", "token"}

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        for key in self.blocked:
            if key in message.casefold():
                message = "sensitive log message suppressed"
                break
        return json.dumps({"level": record.levelname, "event": message}, separators=(",", ":"))


def configure_logging() -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingJsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_schema()
    yield
    await close_websockets()
    await close_clients()


def create_app(*, initialize_schema: bool = True, proxy_settings=None, proxy_session_factory=None) -> FastAPI:
    configure_logging()
    app = FastAPI(title="auth-ingress", lifespan=lifespan if initialize_schema else None)
    from auth_ingress.config import get_settings
    from auth_ingress.repositories.database import SessionLocal

    app.add_middleware(
        ProxyDispatchMiddleware,
        settings=proxy_settings or get_settings(),
        session_factory=proxy_session_factory or SessionLocal,
    )
    app.mount("/static", StaticFiles(directory=WEB_ROOT / "static"), name="static")
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(password_reset.router)
    app.include_router(portal.router)
    app.include_router(services.router)
    app.include_router(admin_services.router)
    app.include_router(admin_groups.router)
    app.include_router(admin_audit.router)
    app.include_router(admin_users.creation_router)
    app.include_router(admin_users.router)

    @app.exception_handler(StarletteHTTPException)
    async def web_http_exception(request: Request, exc: StarletteHTTPException):
        if exc.status_code not in {401, 403, 404}:
            raise exc
        from auth_ingress.config import get_settings as current_settings

        title = "Access denied" if exc.status_code in {401, 403} else "Page not found"
        message = str(exc.detail) if exc.detail else "The requested page is unavailable."
        return template(request, "errors/access_denied.html", current_settings(), title=title, message=message, status_code=exc.status_code)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))[:120]
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers.setdefault("Referrer-Policy", "same-origin")
        logger.info("request_completed method=%s path=%s status=%s correlation_id=%s", request.method, request.url.path, response.status_code, correlation_id)
        return response

    return app


app = create_app()
