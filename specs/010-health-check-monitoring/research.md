# Research: Health Check and Monitoring Indicators

## Public Health Interface

**Decision**: Expose two unauthenticated JSON endpoints: `GET /healthz` for
basic process liveness and `GET /readyz` for readiness to serve authenticated
portal and service-entry journeys.

**Rationale**: Liveness and readiness have different consumers and failure
semantics. Liveness should confirm that the process can answer a request.
Readiness should tell routing and deployment monitors whether the auth boundary
can safely receive user traffic. Keeping them separate avoids overloading one
endpoint while still giving monitors an unambiguous result.

**Alternatives considered**:

- Single `GET /health` endpoint: simpler, but weaker for orchestrators because
  a running process can still be unsafe to route to.
- Admin-only health: protects detail, but does not support automated routing or
  deployment checks.
- Metrics-format endpoint: useful for observability platforms, but adds format
  and operational complexity not required by this feature.

## Readiness Checks

**Decision**: Derive readiness from bounded local checks: application settings
load, database/session availability, installation/bootstrap state, identity
workflow readiness, service catalog state, and audit diagnostic availability.
Do not probe configured downstream service destinations during routine health
checks.

**Rationale**: The auth portal's readiness depends primarily on its own ability
to authenticate users, evaluate access, display services, and emit diagnostic
evidence. Probing downstream destinations can leak private service topology,
create avoidable traffic, make health checks slow, and confuse portal readiness
with individual service uptime.

**Alternatives considered**:

- Probe every downstream destination: provides service availability detail but
  risks slow checks, noisy failures, and private endpoint disclosure.
- Check only process availability: too shallow for a routing readiness signal.
- Treat empty service catalog as unavailable: too strict for first-run or
  partially configured installations where administrators still need access.

## Detailed Monitoring Surface

**Decision**: Add an admin-only monitoring page under the existing
administration surface. The page will reuse the technical UI system, summary
cards, status chips, empty states, and responsive patterns already established
for users, groups, services, and audit pages.

**Rationale**: Operators need richer context than public health responses can
safely expose. Reusing the existing server-rendered admin surface preserves the
current access boundary, keyboard and mobile behavior, and no-external-assets
constraint.

**Alternatives considered**:

- Add a separate dashboard application: unnecessary for the feature scope and
  would create another surface to secure.
- Render detailed indicators on the public health endpoint: violates the
  public-minimal requirement.
- Add only summary cards to existing admin pages: useful but harder to test as
  one monitoring workflow.

## Data and Persistence

**Decision**: Do not add a persistence schema for health checks. Represent
health state and monitoring indicators as derived service-layer view models.
Use existing request-scoped database sessions for local checks.

**Rationale**: The required indicators are snapshots of current operating
conditions. Persisting every check would add storage churn and audit noise
without improving operator value for the current scale.

**Alternatives considered**:

- Store every health check: creates high-volume operational data and violates
  the "routine checks must not flood audit history" requirement.
- Store only the latest health state in the database: adds schema and write
  paths for information that can be recomputed cheaply.
- Use in-memory status only: acceptable for transition detection, but not enough
  by itself for current-state evaluation.

## Diagnostic Evidence

**Decision**: Routine health checks remain read-only and are not audit events.
State transitions and denied attempts to view detailed monitoring produce
non-sensitive diagnostic evidence through structured request logs and redacted
health transition logs.

**Rationale**: Health checks may run frequently. Logging every routine success
as a security event would make the audit trail less useful. Transition logging
preserves incident evidence while respecting audit signal quality and redaction
rules.

**Alternatives considered**:

- Audit every health check: too noisy.
- Audit only admin page views: misses automated readiness transitions.
- No diagnostic evidence beyond response status: insufficient for incident
  review.

## Security Boundary

**Decision**: Public responses expose only broad status, checked time, and broad
reason/check categories. Detailed counts, labels, examples, service catalog
context, identity workflow detail, and recommended remediation are restricted to
authenticated administrators.

**Rationale**: Health endpoints are intentionally accessible to monitors, so
their output must be safe for anonymous access. Administrators still need enough
detail to act quickly during incidents.

**Alternatives considered**:

- Require authentication for all health data: incompatible with common external
  monitors and routing systems.
- Publicly expose detailed JSON: useful for debugging but violates identity and
  service-topology boundaries.
- Add shared secret authentication for monitors: not required for this project
  and introduces token lifecycle concerns.
