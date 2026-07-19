from fastapi.testclient import TestClient

from auth_ingress.config import get_settings
from auth_ingress.main import create_app
from auth_ingress.repositories.database import get_db
from tests.health_monitoring_helpers import assert_no_forbidden_health_terms, assert_public_health_payload


def test_liveness_contract_is_public_and_minimal(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers
    assert_public_health_payload(response.json(), expected_status="alive")
    assert set(response.json()) == {"status", "checked_at"}


def test_readyz_healthy_contract(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    payload = response.json()
    assert_public_health_payload(payload, expected_status="healthy")
    assert payload["reason"] == "all_clear"
    assert {item["key"] for item in payload["checks"]} == {
        "storage",
        "installation",
        "identity_workflows",
        "service_catalog",
        "audit_diagnostics",
    }
    assert all(item["status"] == "healthy" for item in payload["checks"])
    assert_no_forbidden_health_terms(response.text)


def test_readyz_setup_required_contract(db_factory, settings):
    app = create_app(initialize_schema=False, proxy_settings=settings, proxy_session_factory=db_factory)

    def override_db():
        with db_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        response = test_client.get("/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert_public_health_payload(payload, expected_status="setup_required")
    assert payload["reason"] == "setup_required"
    checks = {item["key"]: item["status"] for item in payload["checks"]}
    assert checks["storage"] == "healthy"
    assert checks["installation"] == "setup_required"
    assert checks["identity_workflows"] == "setup_required"
    assert checks["service_catalog"] == "unknown"
    assert checks["audit_diagnostics"] == "healthy"
