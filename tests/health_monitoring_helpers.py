from __future__ import annotations

FORBIDDEN_HEALTH_TERMS = (
    "password",
    "temporary password",
    "reset",
    "session",
    "csrf",
    "cookie",
    "authorization",
    "bearer",
    "secret",
    "token",
    "database_url",
    "sqlite:///",
    "destination",
)


def assert_no_forbidden_health_terms(value: object) -> None:
    rendered = str(value).casefold()
    for term in FORBIDDEN_HEALTH_TERMS:
        assert term.casefold() not in rendered


def assert_public_health_payload(payload: dict, *, expected_status: str) -> None:
    assert payload["status"] == expected_status
    assert payload["checked_at"].endswith("Z")
    assert set(payload) <= {"status", "checked_at", "reason", "checks", "correlation_id"}
    if "checks" in payload:
        for item in payload["checks"]:
            assert set(item) == {"key", "status"}
    assert_no_forbidden_health_terms(payload)
