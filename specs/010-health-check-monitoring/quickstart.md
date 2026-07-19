# Quickstart: Health Check and Monitoring Indicators

## Prerequisites

- Dependencies installed with `uv sync --extra test`.
- Browser test runtime installed for existing Playwright tests.
- A test database can be created through the existing pytest fixtures.

## Validation Commands

Run the focused backend checks:

```bash
uv run pytest tests/contract/test_health_contract.py tests/contract/test_monitoring_ui_contract.py tests/integration/test_health_monitoring.py tests/security/test_health_monitoring_security.py
```

Run the browser check for the admin monitoring page:

```bash
uv run pytest tests/e2e/test_health_monitoring.py
```

Run existing regression coverage for protected journeys:

```bash
uv run pytest tests/contract/test_user_entry_contract.py tests/contract/test_admin_contract.py tests/contract/test_admin_groups_contract.py tests/contract/test_admin_users_contract.py tests/security/test_session_boundary.py
```

## Manual Smoke Scenarios

Start the application:

```bash
uv run uvicorn auth_ingress.main:app --host 127.0.0.1 --port 8000
```

Check liveness:

```bash
curl -i http://127.0.0.1:8000/healthz
```

Expected result: status `200` with JSON containing `status: "alive"` and a
UTC `checked_at` value.

Check readiness:

```bash
curl -i http://127.0.0.1:8000/readyz
```

Expected result when initialized and healthy: status `200`, `status:
"healthy"`, `reason: "all_clear"`, and only broad public check keys.

Expected result when setup is incomplete: status `503`, `status:
"setup_required"`, and no credential, user, service destination, database, or
private configuration details.

Review admin monitoring:

1. Sign in as an active administrator.
2. Open `/admin/monitoring`.
3. Confirm the page shows overall state, last evaluation time, indicator
   statuses, and recommended actions for non-healthy indicators.
4. Confirm the page uses existing admin navigation, summary cards, status
   language, focus states, and responsive layout.

Verify denial behavior:

1. Sign out and request `/admin/monitoring`.
2. Sign in as a non-admin user and request `/admin/monitoring`.
3. Confirm detailed indicator content is not rendered in either denial path.

## Contract References

- Public health response contract: [contracts/health-endpoints.md](./contracts/health-endpoints.md)
- Admin monitoring UI contract: [contracts/monitoring-ui.md](./contracts/monitoring-ui.md)
- Security and diagnostics contract: [contracts/security-diagnostics.md](./contracts/security-diagnostics.md)

## Expected No-Regressions

- Sign-in, sign-out, setup-required, password reset/change, portal service
  listing, service entry, user management, group management, service
  management, audit review, and denial pages continue to behave as before.
- Routine health checks do not create user-visible side effects.
- Public health output and diagnostic logs contain no sensitive values.
