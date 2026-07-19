# Contract: Security and Diagnostic Boundaries

## Public Data Classification

Public health responses are anonymous operational status. They may include only:

- Overall health or liveness state
- UTC evaluation time
- Broad reason category
- Broad check keys and broad check states
- Existing correlation identifier header

They must not disclose secrets, credentials, identities, private destinations,
database details, raw exceptions, environment values, tenant size, or access
topology.

## Admin Data Classification

Admin monitoring indicators may include aggregate, non-sensitive operating
context and recommended actions. They must avoid unnecessary personal data and
must never render credential, session, reset, CSRF, cookie, token, private
destination, database URL, raw SQL, stack trace, or environment value details.

## Diagnostic Events

Routine successful checks:

- Are read-only.
- Must not mutate access or identity data.
- Must not create security audit records for every poll.
- May appear in existing request-completion logs with path, status, and
  correlation identifier.

State transitions:

- Emit a redacted diagnostic log event named `health_state_changed`.
- Include previous status, current status, broad reason, timestamp, and
  correlation identifier when available.
- Exclude raw exception text and sensitive values.

Denied detailed monitoring access:

- Must be denied before detailed indicators are generated or rendered.
- Must be reviewable through existing request diagnostics at minimum: path,
  status, timestamp, and correlation identifier.
- Must not include detailed indicator contents in the denial response.

## Abuse Controls

- Public health checks must perform only bounded local work.
- Health checks must not probe downstream service destinations.
- Health checks must not create sessions, CSRF tokens, reset tokens, temporary
  passwords, launch tickets, or service-proxy cookies.
- Repeated checks must not visibly slow sign-in, service-entry, or admin
  workflows at expected monitoring frequency.

## Redaction Test Vocabulary

Security tests must verify that rendered pages, JSON responses, and logs do not
contain case-insensitive matches for sensitive vocabulary such as:

- `password`
- `temporary password`
- `reset`
- `session`
- `csrf`
- `cookie`
- `authorization`
- `bearer`
- `secret`
- `token`
- `database_url`
- `sqlite:///`
- `destination`
