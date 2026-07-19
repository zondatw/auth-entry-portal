# Data Model: Health Check and Monitoring Indicators

This feature does not add durable tables. The models below are read-only
application view models derived from existing settings, database state, service
catalog data, user/group state, and audit records.

## HealthCheckResult

Represents the machine-readable result returned to automated monitors.

### Fields

- `status`: Overall readiness state. Allowed values: `healthy`, `degraded`,
  `setup_required`, `unavailable`.
- `checked_at`: UTC timestamp for when the result was evaluated.
- `reason`: Broad non-sensitive reason category. Required when status is not
  `healthy`.
- `checks`: Public-safe list of broad check summaries.
- `correlation_id`: Request correlation identifier already assigned by request
  middleware, if available.

### Validation Rules

- `status` must be one of the allowed values.
- `checked_at` must be present and in UTC.
- `reason` must be `all_clear` for healthy responses or a broad reason such as
  `storage_unavailable`, `setup_required`, `identity_degraded`,
  `service_catalog_degraded`, or `audit_unavailable`.
- Public output must not include user emails, display names, group names,
  service destinations, credentials, tokens, session identifiers, CSRF values,
  database URLs, stack traces, or raw exception text.

## MonitoringIndicator

Represents one admin-facing indicator card or row.

### Fields

- `key`: Stable machine-friendly indicator key.
- `label`: Human-readable indicator name.
- `status`: Indicator state. Allowed values: `healthy`, `degraded`,
  `setup_required`, `unavailable`, `unknown`, `stale`.
- `severity`: Display severity. Allowed values: `info`, `warning`, `critical`.
- `last_evaluated_at`: UTC timestamp for the latest evaluation.
- `summary`: Short admin-facing explanation.
- `recommended_action`: Safe next action when attention is needed.
- `public_reason`: Broad reason category safe enough to appear in public
  readiness output.

### Validation Rules

- Every indicator must have `key`, `label`, `status`, `severity`, and
  `last_evaluated_at`.
- `summary` and `recommended_action` must be redacted and must not contain raw
  service destinations, secrets, tokens, private database values, stack traces,
  or unnecessary personal data.
- `unknown` and `stale` indicators must include a recommended action.
- Indicator labels and summaries must remain readable in existing responsive
  admin layouts.

## OperatingCondition

Represents a condition evaluated by the health service.

### Fields

- `category`: Broad category, such as `process`, `configuration`, `storage`,
  `installation`, `identity_workflows`, `service_catalog`, or
  `audit_diagnostics`.
- `required_for_readiness`: Whether failure prevents safe user traffic.
- `status`: Current condition state.
- `safe_detail`: Admin-safe explanation.
- `public_reason`: Public-safe reason category used by readiness output.

### Validation Rules

- Required conditions that cannot be evaluated must make readiness
  `unavailable` or `degraded`.
- First-run setup state must make readiness `setup_required`, not an unexpected
  outage.
- Optional context such as an empty service catalog may be `degraded` or
  `setup_required` only when it affects safe use; otherwise it remains an
  informational admin indicator.

## DiagnosticEvidence

Represents non-sensitive evidence emitted when monitoring state changes or
detailed monitoring access is denied.

### Fields

- `event`: Stable diagnostic event name, such as `health_state_changed` or
  `monitoring_detail_denied`.
- `previous_status`: Previous overall status when available.
- `current_status`: Current overall status.
- `reason`: Broad reason category.
- `correlation_id`: Request correlation identifier when available.
- `occurred_at`: UTC timestamp.

### Validation Rules

- Evidence must be non-sensitive and compatible with existing redacting log
  behavior.
- Routine healthy checks must not create audit records.
- Denied detailed-monitoring requests must be reviewable by path, status, and
  correlation identifier at minimum.

## Relationships

- One `HealthCheckResult` is derived from multiple `MonitoringIndicator`
  values.
- One `MonitoringIndicator` summarizes one or more `OperatingCondition` checks.
- `DiagnosticEvidence` may reference health state transitions derived from
  `HealthCheckResult`, but it does not store full indicator details.

## State Derivation

- `healthy`: All required operating conditions are healthy.
- `setup_required`: The application is reachable but installation bootstrap is
  incomplete.
- `degraded`: The application can answer requests, but one or more required or
  important conditions need attention.
- `unavailable`: The application cannot verify a required condition needed to
  safely serve authenticated user traffic.

## State Transitions

```text
unknown -> healthy
unknown -> setup_required
unknown -> degraded
unknown -> unavailable
healthy -> degraded
healthy -> unavailable
healthy -> setup_required
setup_required -> healthy
setup_required -> degraded
degraded -> healthy
degraded -> unavailable
unavailable -> degraded
unavailable -> healthy
```

Every transition must be eligible for redacted diagnostic logging. Repeated
checks that keep the same state should remain quiet except for normal request
logs.
