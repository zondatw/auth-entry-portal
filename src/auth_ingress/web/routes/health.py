from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from auth_ingress.config import Settings, get_settings
from auth_ingress.repositories.database import get_db
from auth_ingress.security.dependencies import Identity, require_admin
from auth_ingress.services.health_service import evaluate_readiness, liveness_payload
from auth_ingress.web.web import template

router = APIRouter()


@router.get("/healthz")
def healthz():
    return liveness_payload()


@router.get("/readyz")
def readyz(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    result = evaluate_readiness(
        db,
        settings,
        correlation_id=getattr(request.state, "correlation_id", ""),
        emit_transition=True,
    )
    status_code = 200 if result.status == "healthy" else 503
    return JSONResponse(result.public_dict(), status_code=status_code)


@router.get("/admin/monitoring")
def monitoring(
    request: Request,
    identity: Identity = Depends(require_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    result = evaluate_readiness(
        db,
        settings,
        correlation_id=getattr(request.state, "correlation_id", ""),
    )
    return template(
        request,
        "admin/monitoring.html",
        settings,
        user=identity.user,
        overall=result,
        summary=result.admin_summary(),
        indicators=result.admin_checks(),
    )
