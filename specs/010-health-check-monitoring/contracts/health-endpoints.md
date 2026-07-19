# Contract: Public Health Endpoints

## Scope

Public health endpoints are intended for automated deployment, uptime, and
routing monitors. They must be safe for unauthenticated access and must not
reveal sensitive identity, service, storage, or configuration details.

## `GET /healthz`

### Purpose

Reports that the application process is reachable and can return a response.
This endpoint does not prove the portal is ready to serve authenticated user
traffic.

### Authentication

No interactive session required.

### Success Response

Status: `200`

```json
{
  "status": "alive",
  "checked_at": "2026-07-19T00:00:00Z"
}
```

### Contract Rules

- Must not open a user session or require CSRF.
- Must not query or disclose user, group, service, credential, session, token,
  secret, service destination, or database details.
- Must include the normal request correlation and security headers already
  applied by middleware.

## `GET /readyz`

### Purpose

Reports whether auth-ingress is ready to receive user traffic for sign-in,
portal, and service-entry workflows.

### Authentication

No interactive session required.

### Healthy Response

Status: `200`

```json
{
  "status": "healthy",
  "checked_at": "2026-07-19T00:00:00Z",
  "reason": "all_clear",
  "checks": [
    { "key": "storage", "status": "healthy" },
    { "key": "installation", "status": "healthy" },
    { "key": "identity_workflows", "status": "healthy" },
    { "key": "service_catalog", "status": "healthy" },
    { "key": "audit_diagnostics", "status": "healthy" }
  ]
}
```

### Non-Ready Response

Status: `503`

```json
{
  "status": "setup_required",
  "checked_at": "2026-07-19T00:00:00Z",
  "reason": "setup_required",
  "checks": [
    { "key": "storage", "status": "healthy" },
    { "key": "installation", "status": "setup_required" },
    { "key": "identity_workflows", "status": "setup_required" },
    { "key": "service_catalog", "status": "unknown" },
    { "key": "audit_diagnostics", "status": "healthy" }
  ]
}
```

### Allowed Status Values

- `healthy`
- `degraded`
- `setup_required`
- `unavailable`

### Allowed Check Keys

- `storage`
- `installation`
- `identity_workflows`
- `service_catalog`
- `audit_diagnostics`

### Forbidden Public Output

Responses must not include:

- User emails, names, IDs, group names, or group membership details
- Service names, service slugs, internal destinations, private hosts, or URLs
- Credentials, passwords, temporary passwords, reset values, sessions, cookies,
  CSRF values, bearer values, or authorization headers
- Database URLs, table names in error messages, raw SQL, stack traces, exception
  classes, or environment variable values
- Counts that disclose private tenant size or access topology

### Failure Behavior

- If readiness cannot safely evaluate a required condition, return `503` with
  `status: "unavailable"` and a broad `reason`.
- If the installation is not bootstrapped, return `503` with
  `status: "setup_required"` and `reason: "setup_required"`.
- If optional context is incomplete but authenticated journeys can still run,
  return `503` with `status: "degraded"` only when operator attention is needed.
- Raw exceptions must be redacted from responses and logs.
