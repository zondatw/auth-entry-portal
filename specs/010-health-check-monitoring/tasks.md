# Tasks: Health Check and Monitoring Indicators

**Input**: Design documents from `/specs/010-health-check-monitoring/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included because all three stories touch identity, access, public
diagnostics, or administrator-only monitoring behavior, and the project
constitution requires tests for security-sensitive stories.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no
  dependency on an incomplete task in the same phase.
- **[Story]**: Maps task to a user story, such as [US1], [US2], or [US3].
- Every task includes exact repository-relative file paths.

## Path Conventions

- Application code: `src/auth_ingress/`
- Web routes/templates/static assets: `src/auth_ingress/web/`
- Service-layer logic: `src/auth_ingress/services/`
- Tests: `tests/contract/`, `tests/integration/`, `tests/security/`,
  `tests/e2e/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the empty feature files and shared test helper locations needed
by later tasks.

- [X] T001 Create health route module skeleton with APIRouter in src/auth_ingress/web/routes/health.py
- [X] T002 [P] Create health service module skeleton for read-only health view models in src/auth_ingress/services/health_service.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared structures that must exist before any user story can be
implemented.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Define HealthCheckResult, MonitoringIndicator, OperatingCondition, DiagnosticEvidence, allowed status values, allowed check keys, and reason constants in src/auth_ingress/services/health_service.py
- [X] T004 Add public-safe serialization and sensitive-output redaction guard helpers in src/auth_ingress/services/health_service.py
- [X] T005 Register the health router with application middleware coverage in src/auth_ingress/main.py
- [X] T006 [P] Add reusable forbidden-vocabulary and health-response assertion helpers in tests/health_monitoring_helpers.py
- [X] T007 Add health state CSS class placeholders for healthy, degraded, setup-required, unavailable, unknown, and stale states in src/auth_ingress/web/static/portal.css

**Checkpoint**: Foundation ready. User story implementation can now begin.

---

## Phase 3: User Story 1 - Confirm service readiness automatically (Priority: P1) - MVP

**Goal**: Automated monitors can distinguish process liveness from readiness to
serve authenticated portal and service-entry journeys.

**Independent Test**: Request `/healthz` and `/readyz` while the portal is
healthy, setup-required, degraded, and unavailable. The result must be
machine-readable, bounded, and free of sensitive details.

### Tests for User Story 1

Write these tests first and confirm they fail before implementation.

- [X] T008 [P] [US1] Add contract tests for GET /healthz and GET /readyz response shapes, status mapping, security headers, and allowed public check keys in tests/contract/test_health_contract.py
- [X] T009 [P] [US1] Add integration tests for healthy, setup-required, degraded, and unavailable readiness derivation in tests/integration/test_health_monitoring.py
- [X] T010 [P] [US1] Add security tests that public health checks require no session, create no cookies or tokens, avoid CSRF, and redact sensitive values in tests/security/test_health_monitoring_security.py

### Implementation for User Story 1

- [X] T011 [US1] Implement liveness result construction with UTC checked_at serialization in src/auth_ingress/services/health_service.py
- [X] T012 [US1] Implement bounded readiness checks for storage, installation, identity_workflows, service_catalog, and audit_diagnostics without downstream destination probes in src/auth_ingress/services/health_service.py
- [X] T013 [US1] Implement GET /healthz and GET /readyz route handlers using the health service in src/auth_ingress/web/routes/health.py
- [X] T014 [US1] Map readiness statuses to public HTTP 200 or 503 outcomes with broad reason categories in src/auth_ingress/web/routes/health.py
- [X] T015 [US1] Verify public health endpoints do not expose users, groups, service destinations, database URLs, raw exceptions, cookies, sessions, CSRF values, tokens, or credentials in tests/security/test_health_monitoring_security.py

**Checkpoint**: User Story 1 is independently functional and is the suggested
MVP scope.

---

## Phase 4: User Story 2 - Review operator monitoring indicators (Priority: P2)

**Goal**: Authorized operators can open an admin monitoring surface and quickly
identify overall status, affected categories, last evaluation time, and safe
recommended actions.

**Independent Test**: Sign in as an active administrator and open
`/admin/monitoring` across healthy, degraded, empty, setup-required, and
unavailable states. The page must show useful detail without secrets or
unnecessary personal data.

### Tests for User Story 2

Write these tests first and confirm they fail before implementation.

- [X] T016 [P] [US2] Add contract tests for /admin/monitoring required page elements, admin-only content, indicator states, and empty/setup guidance in tests/contract/test_monitoring_ui_contract.py
- [X] T017 [P] [US2] Add Playwright tests for /admin/monitoring responsive layout, non-color status cues, readable long text, and keyboard focus in tests/e2e/test_health_monitoring.py

### Implementation for User Story 2

- [X] T018 [US2] Extend admin-facing MonitoringIndicator builders with severity, summary, last_evaluated_at, public_reason, and recommended_action in src/auth_ingress/services/health_service.py
- [X] T019 [US2] Implement GET /admin/monitoring with require_admin authorization and template rendering in src/auth_ingress/web/routes/health.py
- [X] T020 [US2] Create admin monitoring page with summary grid, indicator details, status chips, recommendations, and empty/setup states in src/auth_ingress/web/templates/admin/monitoring.html
- [X] T021 [US2] Add administrator navigation link for Monitoring in src/auth_ingress/web/templates/base.html
- [X] T022 [US2] Complete monitoring indicator layout, wrapping, focus, contrast, and state styles in src/auth_ingress/web/static/portal.css

**Checkpoint**: User Story 2 works independently after Foundation and provides
admin monitoring without changing existing admin workflows.

---

## Phase 5: User Story 3 - Investigate health changes safely (Priority: P3)

**Goal**: Administrators can investigate health changes through non-sensitive
diagnostic evidence, while routine checks stay quiet and detailed monitoring
remains admin-only.

**Independent Test**: Trigger a degraded condition, restore it, review
diagnostic evidence, and confirm routine health checks do not flood security
audit records or leak detailed indicator data to unauthorized users.

### Tests for User Story 3

Write these tests first and confirm they fail before implementation.

- [X] T023 [P] [US3] Add integration tests for health state transition detection and routine-check quiet behavior in tests/integration/test_health_monitoring.py
- [X] T024 [P] [US3] Add security tests for denied /admin/monitoring access, no detailed indicator leaks, no audit flood, and sensitive vocabulary redaction in tests/security/test_health_monitoring_security.py

### Implementation for User Story 3

- [X] T025 [US3] Implement in-memory health state transition tracking and redacted health_state_changed log emission in src/auth_ingress/services/health_service.py
- [X] T026 [US3] Ensure /admin/monitoring applies require_admin before evaluating or rendering detailed indicators in src/auth_ingress/web/routes/health.py
- [X] T027 [US3] Keep routine health checks free of audit_service.record_event writes while preserving request diagnostics in src/auth_ingress/services/health_service.py and src/auth_ingress/web/routes/health.py

**Checkpoint**: All user stories are independently functional and security
diagnostics remain non-sensitive.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, verification, and no-regression coverage across the
feature.

- [X] T028 [P] Document /healthz, /readyz, /admin/monitoring, health state meanings, and redaction boundaries for operators in README.md
- [X] T029 [P] Update validation guidance if implementation details changed in specs/010-health-check-monitoring/quickstart.md
- [X] T030 Run focused backend validation from quickstart for tests/contract/test_health_contract.py, tests/contract/test_monitoring_ui_contract.py, tests/integration/test_health_monitoring.py, and tests/security/test_health_monitoring_security.py
- [X] T031 Run browser validation for admin monitoring in tests/e2e/test_health_monitoring.py
- [X] T032 Run existing protected-journey regressions for tests/contract/test_user_entry_contract.py, tests/contract/test_admin_contract.py, tests/contract/test_admin_groups_contract.py, tests/contract/test_admin_users_contract.py, and tests/security/test_session_boundary.py
- [X] T033 Review public JSON, rendered admin monitoring HTML, and logs against contracts/security-diagnostics.md using tests/health_monitoring_helpers.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user
  stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion.
- **User Story 2 (Phase 4)**: Depends on Foundational completion and can be
  implemented after or alongside US1, but uses the shared health service.
- **User Story 3 (Phase 5)**: Depends on Foundational completion and is easiest
  after US1 and US2 route/service boundaries exist.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on other stories after Foundation.
- **User Story 2 (P2)**: No dependency on US3; reuses Foundation and may reuse
  US1 health result builders.
- **User Story 3 (P3)**: Builds on the same service and route boundaries used by
  US1 and US2, but remains independently testable through diagnostics and denial
  behavior.

### Within Each User Story

- Tests must be written first and fail before implementation.
- Shared view models and constants must exist before services.
- Service behavior must exist before route handlers or templates that consume
  it.
- Route handlers must exist before browser and manual smoke validation can pass.
- Each story must pass its independent test before continuing to the next
  priority when working sequentially.

### Parallel Opportunities

- T001 and T002 can run in parallel after agreeing on module names.
- T006 can run in parallel with T003, T004, T005, and T007.
- T008, T009, and T010 can run in parallel before US1 implementation.
- T016 and T017 can run in parallel before US2 implementation.
- T023 and T024 can run in parallel before US3 implementation.
- T028 and T029 can run in parallel during polish.

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "T008 [P] [US1] Add contract tests for GET /healthz and GET /readyz response shapes, status mapping, security headers, and allowed public check keys in tests/contract/test_health_contract.py"
Task: "T009 [P] [US1] Add integration tests for healthy, setup-required, degraded, and unavailable readiness derivation in tests/integration/test_health_monitoring.py"
Task: "T010 [P] [US1] Add security tests that public health checks require no session, create no cookies or tokens, avoid CSRF, and redact sensitive values in tests/security/test_health_monitoring_security.py"
```

## Parallel Example: User Story 2

```bash
# Launch US2 page contract and browser checks together:
Task: "T016 [P] [US2] Add contract tests for /admin/monitoring required page elements, admin-only content, indicator states, and empty/setup guidance in tests/contract/test_monitoring_ui_contract.py"
Task: "T017 [P] [US2] Add Playwright tests for /admin/monitoring responsive layout, non-color status cues, readable long text, and keyboard focus in tests/e2e/test_health_monitoring.py"
```

## Parallel Example: User Story 3

```bash
# Launch US3 diagnostics and denial tests together:
Task: "T023 [P] [US3] Add integration tests for health state transition detection and routine-check quiet behavior in tests/integration/test_health_monitoring.py"
Task: "T024 [P] [US3] Add security tests for denied /admin/monitoring access, no detailed indicator leaks, no audit flood, and sensitive vocabulary redaction in tests/security/test_health_monitoring_security.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Stop and validate `/healthz` and `/readyz` independently.
5. Commit or demo the MVP once public health checks pass and redaction is clean.

### Incremental Delivery

1. Complete Setup and Foundation.
2. Add User Story 1, then run focused health endpoint tests.
3. Add User Story 2, then run admin monitoring contract and browser tests.
4. Add User Story 3, then run diagnostics and security tests.
5. Run polish validation and protected-journey regressions.

### Parallel Team Strategy

With multiple developers:

1. Complete Setup and Foundation together.
2. Assign US1 endpoint tests and implementation to one developer.
3. Assign US2 admin UI tests and implementation to another developer.
4. Assign US3 diagnostics and security tests to another developer after route
   boundaries are stable.
5. Merge by story checkpoint and rerun quickstart validation after each merge.

---

## Notes

- [P] tasks use different files or can be performed without blocking other
  incomplete tasks in the same phase.
- [US1], [US2], and [US3] labels map to the user stories in spec.md.
- Keep all health checks read-only and bounded to local state.
- Do not expose credentials, tokens, sessions, CSRF values, service
  destinations, database URLs, raw exceptions, or unnecessary personal data.
- Do not add a database migration, background job, external metrics service, or
  downstream service probing unless the plan is amended first.
