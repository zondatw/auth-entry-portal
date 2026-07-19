from tests.conftest import sign_in
from tests.health_monitoring_helpers import assert_no_forbidden_health_terms
from tests.ui_style_helpers import assert_contains_markers, assert_safe_summary_cards


def test_admin_monitoring_page_contract(client, csrf):
    sign_in(client, csrf, email="admin@example.test")

    response = client.get("/admin/monitoring")

    assert response.status_code == 200
    assert_contains_markers(response.text)
    assert_safe_summary_cards(response.text)
    for text in (
        "Health monitoring",
        "Overall health",
        "Last evaluated",
        "Recommended action",
        "Storage",
        "Installation",
        "Identity workflows",
        "Service catalog",
        "Audit diagnostics",
    ):
        assert text in response.text
    assert "status-healthy" in response.text
    assert_no_forbidden_health_terms(response.text)


def test_admin_monitoring_denies_detail_to_signed_out_and_non_admin(client, csrf):
    signed_out = client.get("/admin/monitoring")
    assert signed_out.status_code == 401
    assert "Storage" not in signed_out.text
    assert "Service catalog" not in signed_out.text
    assert "Recommended action" not in signed_out.text

    sign_in(client, csrf, email="member@example.test")
    non_admin = client.get("/admin/monitoring")
    assert non_admin.status_code == 403
    assert "Storage" not in non_admin.text
    assert "Service catalog" not in non_admin.text
    assert "Recommended action" not in non_admin.text


def test_admin_monitoring_shows_empty_catalog_guidance(client, csrf, db):
    from auth_ingress.models import AccessRule, ServiceEntry

    db.query(AccessRule).delete()
    db.query(ServiceEntry).delete()
    db.commit()
    sign_in(client, csrf, email="admin@example.test")

    response = client.get("/admin/monitoring")

    assert response.status_code == 200
    assert "No service entries are configured for users." in response.text
    assert "Add a service entry and connect it to an active group." in response.text
    assert "status-degraded" in response.text
