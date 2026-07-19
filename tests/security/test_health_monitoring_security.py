from sqlalchemy import func, select

from auth_ingress.models import AuditEvent
from tests.conftest import sign_in
from tests.health_monitoring_helpers import assert_no_forbidden_health_terms


def test_public_health_checks_are_anonymous_and_create_no_auth_artifacts(client):
    for path in ("/healthz", "/readyz"):
        response = client.get(path)

        assert response.status_code in {200, 503}
        assert "set-cookie" not in response.headers
        assert "auth_portal_session" not in response.text
        assert_no_forbidden_health_terms(response.text)


def test_public_health_checks_do_not_create_audit_records(client, db):
    before = db.scalar(select(func.count(AuditEvent.id))) or 0

    for _ in range(3):
        client.get("/healthz")
        client.get("/readyz")

    after = db.scalar(select(func.count(AuditEvent.id))) or 0
    assert after == before


def test_public_health_output_redacts_configuration_and_identity_data(client):
    response = client.get("/readyz")

    assert "admin@example.test" not in response.text
    assert "staff" not in response.text
    assert "mock://demo" not in response.text
    assert "sqlite:///" not in response.text
    assert_no_forbidden_health_terms(response.text)


def test_admin_monitoring_denial_happens_before_indicator_evaluation(client, csrf, monkeypatch):
    import auth_ingress.web.routes.health as health_routes

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("monitoring detail was evaluated before authorization")

    monkeypatch.setattr(health_routes, "evaluate_readiness", fail_if_called)

    signed_out = client.get("/admin/monitoring")
    assert signed_out.status_code == 401
    assert "Storage" not in signed_out.text
    assert "Recommended action" not in signed_out.text

    sign_in(client, csrf, email="member@example.test")
    non_admin = client.get("/admin/monitoring")
    assert non_admin.status_code == 403
    assert "Storage" not in non_admin.text
    assert "Recommended action" not in non_admin.text


def test_admin_monitoring_and_denials_do_not_create_audit_flood(client, csrf, db):
    before = db.scalar(select(func.count(AuditEvent.id))) or 0

    client.get("/admin/monitoring")
    sign_in(client, csrf, email="member@example.test")
    client.get("/admin/monitoring")

    after = db.scalar(select(func.count(AuditEvent.id))) or 0
    assert after == before + 1


def test_admin_monitoring_output_redacts_sensitive_vocabulary(client, csrf):
    sign_in(client, csrf, email="admin@example.test")

    response = client.get("/admin/monitoring")

    assert response.status_code == 200
    assert_no_forbidden_health_terms(response.text)
