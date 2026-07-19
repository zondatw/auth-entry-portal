# Implementation Plan: Health Check and Monitoring Indicators

**Branch**: `010-health-check-monitoring` | **Date**: 2026-07-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-health-check-monitoring/spec.md`

## Summary

Add a read-only health and monitoring surface for auth-ingress. Automated
systems get minimal liveness and readiness results suitable for deployment and
routing decisions, while authenticated administrators get a richer monitoring
view with non-sensitive indicators, last evaluation time, and safe remediation
guidance. The technical approach is to add a small health service that derives
state from existing settings, database/session access, installation state,
service catalog records, and audit diagnostics, expose public JSON health
routes, render an admin-only monitoring page with the existing UI system, and
record only non-sensitive diagnostic evidence for state changes and denied
detail access.

## Technical Context

**Language/Version**: Python 3.12+ application; package currently supports
Python 3.12, 3.13, and 3.14.

**Primary Dependencies**: Existing FastAPI/Starlette routing, SQLAlchemy
sessions, Jinja2 server-rendered templates, local static CSS, pytest, and
Playwright browser tests. No new third-party monitoring service, metrics SDK,
frontend framework, hosted script, or hosted asset.

**Storage**: Existing SQLite-backed SQLAlchemy persistence. No schema migration
is planned; health and monitoring state is derived read-only from existing
settings, installation state, users, groups, service entries, access rules, and
audit records. Non-sensitive transition evidence uses structured application
logs rather than a new health-check table.

**Testing**: pytest contract tests for public health responses and admin
monitoring contracts, integration tests for derived states across healthy,
setup-required, degraded, and unavailable conditions, security tests for
redaction and authorization, and Playwright e2e tests for the admin monitoring
surface.

**Target Platform**: Desktop and mobile browsers plus automated HTTP monitors
served by the existing auth-ingress web application.

**Project Type**: Single Python server-rendered web application with small JSON
health endpoints.

**Performance Goals**: Public health checks complete within 5 seconds in all
specified states. The readiness check stays bounded to local application state
and does not probe downstream service destinations. Routine checks do not create
visible delay in sign-in or service-entry journeys.

**Constraints**: Preserve existing authentication, authorization, session,
CSRF, password, service-entry, management-form, proxy, and audit behavior.
Public health output must be minimal and non-sensitive. Detailed indicators are
admin-only. Routine checks must be read-only, must not mutate access data, and
must not flood security audit history. Cache-control and redaction behavior must
remain consistent with the existing request middleware.

**Scale/Scope**: Initial scope targets the current small internal portal:
hundreds of users, tens of services, existing local persistence, one application
process per deployment in common use, and standard uptime/deployment monitors.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Secure Identity Boundaries**: PASS. The plan separates public minimal health
  from admin-only monitoring detail. Credentials, sessions, CSRF values, reset
  data, service destinations, storage URLs, and unnecessary personal data are
  explicitly excluded from public output, rendered indicators, logs, and
  examples.
- **User-Centered Authentication Flows**: PASS. Healthy, degraded,
  setup-required, unavailable, stale, unknown, denied, and empty states are
  covered in the spec and contracts. Existing user journeys remain unchanged.
- **Testable Security Behavior**: PASS. Planned tests cover healthy readiness,
  setup-required readiness, unavailable storage/configuration, stale or unknown
  indicators, admin-only detailed monitoring, denied access, redaction, and
  existing journey regressions.
- **Observable and Auditable Operations**: PASS. Routine checks are not stored
  as security audit events. State transitions and denied detail access produce
  non-sensitive diagnostic evidence through existing structured request logging
  and dedicated redacted health transition logging.
- **Simple, Explicit Architecture**: PASS. The implementation stays in the
  existing web app with one health service, one route module, one admin
  template, and focused tests. No external monitoring provider, background job,
  schema change, or downstream probing is introduced.

## Project Structure

### Documentation (this feature)

```text
specs/010-health-check-monitoring/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── health-endpoints.md
│   ├── monitoring-ui.md
│   └── security-diagnostics.md
└── tasks.md
```

### Source Code (repository root)

```text
src/auth_ingress/
├── main.py
├── services/
│   ├── health_service.py
│   └── audit_service.py
└── web/
    ├── routes/
    │   ├── health.py
    │   └── admin_*.py
    ├── templates/
    │   ├── base.html
    │   └── admin/
    │       └── monitoring.html
    └── static/
        └── portal.css

tests/
├── contract/
│   ├── test_health_contract.py
│   └── test_monitoring_ui_contract.py
├── integration/
│   └── test_health_monitoring.py
├── security/
│   └── test_health_monitoring_security.py
└── e2e/
    └── test_health_monitoring.py
```

**Structure Decision**: Keep the feature inside the existing server-rendered
auth-ingress application. `health_service.py` owns derived read-only state and
redacted transition evidence. `web/routes/health.py` exposes public health JSON
and an admin-only monitoring page. Existing admin templates, `base.html`, and
`portal.css` provide navigation and visual treatment. Tests follow the existing
contract/integration/security/e2e split.

## Complexity Tracking

No constitution violations are accepted for this plan.

## Post-Design Constitution Check

- **Secure Identity Boundaries**: PASS. Contracts define public response fields,
  admin-only fields, forbidden values, and redaction checks.
- **User-Centered Authentication Flows**: PASS. Quickstart covers liveness,
  readiness, setup-required, degraded, admin review, denied detail access, and
  no-regression journeys.
- **Testable Security Behavior**: PASS. Contracts and quickstart map security
  requirements to contract, integration, security, and browser tests.
- **Observable and Auditable Operations**: PASS. Diagnostic evidence is bounded
  to structured request logs and health transition logs. Routine monitor checks
  remain read-only and do not flood audit history.
- **Simple, Explicit Architecture**: PASS. No new runtime dependency, external
  provider, database migration, background job, or downstream service probing is
  required.
