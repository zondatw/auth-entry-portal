# Contract: Admin Monitoring UI

## Scope

The admin monitoring UI gives authorized operators a richer view of health and
operating indicators while preserving the existing identity and administration
boundary.

## `GET /admin/monitoring`

### Authentication

Requires an authenticated user with active administrator access.

### Denial Behavior

- Signed-out users receive the existing authentication-required behavior.
- Non-admin or inactive users receive the existing administrator-denied
  behavior.
- Denied responses must not render indicator names, counts, service catalog
  context, user context, remediation text, or private configuration detail.

### Required Page Elements

- Page heading that identifies the view as monitoring or health status.
- Overall health state with last evaluation time.
- Indicator summary grid using the existing summary-card/status-chip visual
  language.
- Indicator details for storage, installation, identity workflows, service
  catalog, and audit diagnostics.
- Recommended action for each non-healthy, stale, unknown, setup-required, or
  unavailable indicator.
- Link or navigation affordance from the existing administration surface.
- Empty/setup guidance when users, groups, services, or audit events do not yet
  exist.

### Indicator Display Rules

- Healthy, degraded, setup-required, unavailable, unknown, and stale states must
  be visually and textually distinct.
- Color must not be the only state cue.
- Long labels, summaries, and recommended actions must wrap safely on desktop
  and mobile.
- The page must not introduce horizontal page overflow outside intentional
  scroll regions.
- The page must use existing focus, contrast, table/card, alert, and responsive
  patterns.

### Forbidden Admin Output

Even for administrators, the page must not render:

- Passwords, temporary passwords, reset values, session identifiers, CSRF values,
  cookies, bearer values, or authorization headers
- Full internal service destinations, database URLs, raw SQL, stack traces, or
  environment variable values
- User data that is not needed to understand aggregate operating health

### Acceptance Checks

- An administrator can identify the overall state, affected category, and
  recommended action within 30 seconds.
- The page renders useful healthy, degraded, setup-required, unknown, stale, and
  empty states.
- Existing admin pages remain reachable and retain their current behavior.
