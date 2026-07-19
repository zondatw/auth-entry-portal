import logging

from fastapi.testclient import TestClient

from auth_ingress.config import get_settings
from auth_ingress.main import create_app
from auth_ingress.models import AccessRule, ServiceEntry
from auth_ingress.repositories.database import get_db
from auth_ingress.services.health_service import evaluate_readiness, reset_transition_state
from tests.health_monitoring_helpers import assert_public_health_payload
from tests.health_monitoring_helpers import assert_no_forbidden_health_terms


def test_readyz_reports_degraded_when_initialized_catalog_is_empty(client, db):
    db.query(AccessRule).delete()
    db.query(ServiceEntry).delete()
    db.commit()

    response = client.get("/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert_public_health_payload(payload, expected_status="degraded")
    assert payload["reason"] == "service_catalog_degraded"
    checks = {item["key"]: item["status"] for item in payload["checks"]}
    assert checks["service_catalog"] == "degraded"
    assert checks["storage"] == "healthy"


def test_readyz_reports_unavailable_when_storage_check_fails(db_factory, settings):
    class BrokenDb:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("database unavailable")

        def scalar(self, *_args, **_kwargs):
            raise RuntimeError("database unavailable")

    app = create_app(initialize_schema=False, proxy_settings=settings, proxy_session_factory=db_factory)

    def override_db():
        yield BrokenDb()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        response = test_client.get("/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert_public_health_payload(payload, expected_status="unavailable")
    assert payload["reason"] == "storage_unavailable"
    checks = {item["key"]: item["status"] for item in payload["checks"]}
    assert checks["storage"] == "unavailable"
    assert checks["installation"] == "unknown"


def test_health_state_transitions_emit_redacted_diagnostic_logs(db, settings, caplog):
    reset_transition_state()
    caplog.set_level(logging.INFO, logger="auth_ingress")

    healthy = evaluate_readiness(db, settings, correlation_id="transition-test", emit_transition=True)
    db.query(AccessRule).delete()
    db.query(ServiceEntry).delete()
    db.commit()
    degraded = evaluate_readiness(db, settings, correlation_id="transition-test", emit_transition=True)

    assert healthy.status == "healthy"
    assert degraded.status == "degraded"
    assert "health_state_changed" in caplog.text
    assert "current_status=healthy" in caplog.text
    assert "current_status=degraded" in caplog.text
    assert_no_forbidden_health_terms(caplog.text)


def test_repeated_same_health_state_stays_quiet(db, settings, caplog):
    reset_transition_state()
    caplog.set_level(logging.INFO, logger="auth_ingress")

    evaluate_readiness(db, settings, correlation_id="quiet-test", emit_transition=True)
    caplog.clear()
    evaluate_readiness(db, settings, correlation_id="quiet-test", emit_transition=True)
    evaluate_readiness(db, settings, correlation_id="quiet-test", emit_transition=True)

    assert "health_state_changed" not in caplog.text
