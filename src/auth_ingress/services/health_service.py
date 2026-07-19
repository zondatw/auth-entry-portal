from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import re
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from auth_ingress.config import Settings
from auth_ingress.models import AccessRule, AuditEvent, Group, InstallationState, ServiceEntry, User

logger = logging.getLogger("auth_ingress")

PUBLIC_STATUSES = {"healthy", "degraded", "setup_required", "unavailable"}
INDICATOR_STATUSES = PUBLIC_STATUSES | {"unknown", "stale"}
SEVERITIES = {"info", "warning", "critical"}
CHECK_KEYS = ("storage", "installation", "identity_workflows", "service_catalog", "audit_diagnostics")
ALL_CLEAR = "all_clear"
SENSITIVE_PATTERNS = (
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
_SENSITIVE_RE = re.compile("|".join(re.escape(term) for term in SENSITIVE_PATTERNS), re.IGNORECASE)
_previous_health_status: str | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp(value: datetime | None = None) -> str:
    current = value or utcnow()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def contains_sensitive_text(value: Any) -> bool:
    return bool(_SENSITIVE_RE.search(str(value)))


def safe_text(value: str, *, fallback: str = "unavailable") -> str:
    cleaned = " ".join(str(value).split())[:160]
    return fallback if contains_sensitive_text(cleaned) else cleaned


@dataclass(frozen=True, slots=True)
class MonitoringIndicator:
    key: str
    label: str
    status: str
    severity: str
    last_evaluated_at: datetime
    summary: str
    recommended_action: str
    public_reason: str

    def __post_init__(self) -> None:
        if self.status not in INDICATOR_STATUSES:
            raise ValueError("invalid indicator status")
        if self.severity not in SEVERITIES:
            raise ValueError("invalid indicator severity")
        if contains_sensitive_text((self.summary, self.recommended_action)):
            raise ValueError("indicator text contains sensitive content")

    def public_dict(self) -> dict[str, str]:
        return {"key": self.key, "status": self.status}

    def admin_dict(self) -> dict[str, str]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status,
            "severity": self.severity,
            "last_evaluated_at": utc_timestamp(self.last_evaluated_at),
            "summary": self.summary,
            "recommended_action": self.recommended_action,
            "public_reason": self.public_reason,
        }


@dataclass(frozen=True, slots=True)
class OperatingCondition:
    category: str
    required_for_readiness: bool
    status: str
    safe_detail: str
    public_reason: str

    def __post_init__(self) -> None:
        if self.status not in INDICATOR_STATUSES:
            raise ValueError("invalid condition status")
        if contains_sensitive_text(self.safe_detail):
            raise ValueError("condition detail contains sensitive content")


@dataclass(frozen=True, slots=True)
class DiagnosticEvidence:
    event: str
    previous_status: str | None
    current_status: str
    reason: str
    correlation_id: str
    occurred_at: datetime

    def log_message(self) -> str:
        return (
            f"{self.event} previous_status={self.previous_status or 'unknown'} "
            f"current_status={self.current_status} reason={self.reason} "
            f"correlation_id={safe_text(self.correlation_id, fallback='')}"
        )


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    status: str
    checked_at: datetime
    reason: str
    checks: tuple[MonitoringIndicator, ...] = field(default_factory=tuple)
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if self.status not in PUBLIC_STATUSES:
            raise ValueError("invalid health status")
        if self.reason != ALL_CLEAR and contains_sensitive_text(self.reason):
            raise ValueError("health reason contains sensitive content")

    def public_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "checked_at": utc_timestamp(self.checked_at),
            "reason": self.reason,
            "checks": [indicator.public_dict() for indicator in self.checks],
        }
        if self.correlation_id:
            payload["correlation_id"] = safe_text(self.correlation_id, fallback="")
        assert_public_safe(payload)
        return payload

    def admin_summary(self) -> list[dict[str, object]]:
        unhealthy = sum(1 for check in self.checks if check.status != "healthy")
        critical = sum(1 for check in self.checks if check.severity == "critical")
        return [
            {
                "label": "Overall health",
                "value": self.status.replace("_", " "),
                "status": self.status,
                "hint": "Current readiness for user traffic.",
            },
            {
                "label": "Indicators",
                "value": len(self.checks),
                "status": "neutral",
                "hint": "Local operating categories evaluated.",
            },
            {
                "label": "Needs attention",
                "value": unhealthy,
                "status": "warning" if unhealthy else "success",
                "hint": "Indicators not currently healthy.",
            },
            {
                "label": "Critical",
                "value": critical,
                "status": "danger" if critical else "success",
                "hint": "Conditions blocking safe readiness.",
            },
        ]

    def admin_checks(self) -> list[dict[str, str]]:
        return [indicator.admin_dict() for indicator in self.checks]


def assert_public_safe(payload: Any) -> None:
    if contains_sensitive_text(payload):
        raise ValueError("health payload contains sensitive content")


def liveness_payload() -> dict[str, str]:
    payload = {"status": "alive", "checked_at": utc_timestamp()}
    assert_public_safe(payload)
    return payload


def _indicator(
    key: str,
    label: str,
    status: str,
    severity: str,
    summary: str,
    recommended_action: str,
    public_reason: str,
    checked_at: datetime,
) -> MonitoringIndicator:
    return MonitoringIndicator(
        key=key,
        label=label,
        status=status,
        severity=severity,
        last_evaluated_at=checked_at,
        summary=safe_text(summary, fallback="Status detail unavailable."),
        recommended_action=safe_text(recommended_action, fallback="Review application diagnostics."),
        public_reason=public_reason,
    )


def _unknown_indicator(key: str, label: str, checked_at: datetime) -> MonitoringIndicator:
    return _indicator(
        key,
        label,
        "unknown",
        "warning",
        "This condition could not be evaluated because an earlier check failed.",
        "Restore required operating conditions, then refresh monitoring.",
        f"{key}_unknown",
        checked_at,
    )


def _count(db: Session, statement) -> int:
    return int(db.scalar(statement) or 0)


def _storage_indicator(db: Session, checked_at: datetime) -> MonitoringIndicator:
    try:
        db.execute(text("SELECT 1")).scalar_one()
    except Exception:
        return _indicator(
            "storage",
            "Storage",
            "unavailable",
            "critical",
            "Storage cannot be reached for local readiness checks.",
            "Restore local persistence access before routing user traffic here.",
            "storage_unavailable",
            checked_at,
        )
    return _indicator(
        "storage",
        "Storage",
        "healthy",
        "info",
        "Local persistence is reachable for readiness checks.",
        "No action needed.",
        ALL_CLEAR,
        checked_at,
    )


def _installation_indicator(db: Session, checked_at: datetime) -> tuple[MonitoringIndicator, int, str | None]:
    state = db.get(InstallationState, 1)
    user_count = _count(db, select(func.count(User.id)))
    state_name = state.state if state is not None else None
    if user_count == 0 and state_name in {None, "needs_bootstrap"}:
        return (
            _indicator(
                "installation",
                "Installation",
                "setup_required",
                "warning",
                "First administrator setup is still required.",
                "Run the local bootstrap flow before routing user traffic here.",
                "setup_required",
                checked_at,
            ),
            user_count,
            state_name,
        )
    if state_name not in {None, "initialized", "needs_bootstrap"}:
        return (
            _indicator(
                "installation",
                "Installation",
                "degraded",
                "warning",
                "Installation state is not recognized.",
                "Review installation state before routing user traffic here.",
                "installation_degraded",
                checked_at,
            ),
            user_count,
            state_name,
        )
    return (
        _indicator(
            "installation",
            "Installation",
            "healthy",
            "info",
            "Installation has portal users and can proceed with identity checks.",
            "No action needed.",
            ALL_CLEAR,
            checked_at,
        ),
        user_count,
        state_name,
    )


def _identity_indicator(db: Session, checked_at: datetime, installation_status: str) -> MonitoringIndicator:
    if installation_status == "setup_required":
        return _indicator(
            "identity_workflows",
            "Identity workflows",
            "setup_required",
            "warning",
            "Identity workflows are waiting for first administrator setup.",
            "Complete setup before expecting sign-in or administration to work.",
            "setup_required",
            checked_at,
        )
    active_users = _count(db, select(func.count(User.id)).where(User.status == "active"))
    active_admins = _count(
        db,
        select(func.count(User.id)).where(
            User.status == "active",
            User.credential_status == "active",
            User.is_admin.is_(True),
        ),
    )
    if active_admins == 0:
        return _indicator(
            "identity_workflows",
            "Identity workflows",
            "degraded",
            "critical",
            "No active administrator is available for management recovery.",
            "Restore an active administrator account.",
            "identity_degraded",
            checked_at,
        )
    if active_users == 0:
        return _indicator(
            "identity_workflows",
            "Identity workflows",
            "degraded",
            "warning",
            "No active user account is currently available.",
            "Create or reactivate a user account.",
            "identity_degraded",
            checked_at,
        )
    return _indicator(
        "identity_workflows",
        "Identity workflows",
        "healthy",
        "info",
        "Active users and administrators are available.",
        "No action needed.",
        ALL_CLEAR,
        checked_at,
    )


def _service_catalog_indicator(db: Session, checked_at: datetime, installation_status: str) -> MonitoringIndicator:
    if installation_status == "setup_required":
        return _indicator(
            "service_catalog",
            "Service catalog",
            "unknown",
            "warning",
            "Service catalog readiness is deferred until setup is complete.",
            "Complete setup, then configure service entries as needed.",
            "service_catalog_unknown",
            checked_at,
        )
    service_count = _count(db, select(func.count(ServiceEntry.id)))
    enabled_count = _count(db, select(func.count(ServiceEntry.id)).where(ServiceEntry.status == "enabled"))
    linked_count = _count(
        db,
        select(func.count(func.distinct(AccessRule.service_entry_id)))
        .select_from(AccessRule)
        .join(ServiceEntry, ServiceEntry.id == AccessRule.service_entry_id)
        .join(Group, Group.id == AccessRule.group_id)
        .where(ServiceEntry.status == "enabled", Group.status == "active"),
    )
    if service_count == 0:
        return _indicator(
            "service_catalog",
            "Service catalog",
            "degraded",
            "warning",
            "No service entries are configured for users.",
            "Add a service entry and connect it to an active group.",
            "service_catalog_degraded",
            checked_at,
        )
    if enabled_count == 0 or linked_count == 0:
        return _indicator(
            "service_catalog",
            "Service catalog",
            "degraded",
            "warning",
            "Configured service entries need enabled access rules.",
            "Enable at least one service entry and connect it to an active group.",
            "service_catalog_degraded",
            checked_at,
        )
    return _indicator(
        "service_catalog",
        "Service catalog",
        "healthy",
        "info",
        "Enabled service entries are connected to active groups.",
        "No action needed.",
        ALL_CLEAR,
        checked_at,
    )


def _audit_indicator(db: Session, checked_at: datetime) -> MonitoringIndicator:
    try:
        _count(db, select(func.count(AuditEvent.id)))
    except Exception:
        return _indicator(
            "audit_diagnostics",
            "Audit diagnostics",
            "unavailable",
            "critical",
            "Audit diagnostics cannot be evaluated.",
            "Review local persistence and application diagnostics.",
            "audit_unavailable",
            checked_at,
        )
    return _indicator(
        "audit_diagnostics",
        "Audit diagnostics",
        "healthy",
        "info",
        "Audit diagnostics can be queried.",
        "No action needed.",
        ALL_CLEAR,
        checked_at,
    )


def _overall_status(checks: tuple[MonitoringIndicator, ...]) -> tuple[str, str]:
    if any(check.key == "storage" and check.status == "unavailable" for check in checks):
        return "unavailable", "storage_unavailable"
    if any(check.status == "setup_required" for check in checks):
        return "setup_required", "setup_required"
    for reason in (
        "identity_degraded",
        "service_catalog_degraded",
        "audit_unavailable",
        "installation_degraded",
        "installation_unavailable",
    ):
        if any(check.public_reason == reason for check in checks):
            return ("unavailable" if reason.endswith("_unavailable") else "degraded"), reason
    if any(check.status in {"degraded", "unavailable", "unknown", "stale"} for check in checks):
        first = next(check for check in checks if check.status != "healthy")
        return "degraded", first.public_reason
    return "healthy", ALL_CLEAR


def evaluate_readiness(
    db: Session,
    settings: Settings,
    *,
    correlation_id: str = "",
    emit_transition: bool = False,
) -> HealthCheckResult:
    del settings
    checked_at = utcnow()
    storage = _storage_indicator(db, checked_at)
    if storage.status == "unavailable":
        checks = (
            storage,
            _unknown_indicator("installation", "Installation", checked_at),
            _unknown_indicator("identity_workflows", "Identity workflows", checked_at),
            _unknown_indicator("service_catalog", "Service catalog", checked_at),
            _unknown_indicator("audit_diagnostics", "Audit diagnostics", checked_at),
        )
    else:
        try:
            installation, _user_count, _state_name = _installation_indicator(db, checked_at)
            checks = (
                storage,
                installation,
                _identity_indicator(db, checked_at, installation.status),
                _service_catalog_indicator(db, checked_at, installation.status),
                _audit_indicator(db, checked_at),
            )
        except Exception:
            checks = (
                storage,
                _indicator(
                    "installation",
                    "Installation",
                    "unavailable",
                    "critical",
                    "Installation readiness could not be evaluated.",
                    "Review local persistence and application diagnostics.",
                    "installation_unavailable",
                    checked_at,
                ),
                _unknown_indicator("identity_workflows", "Identity workflows", checked_at),
                _unknown_indicator("service_catalog", "Service catalog", checked_at),
                _unknown_indicator("audit_diagnostics", "Audit diagnostics", checked_at),
            )
    status, reason = _overall_status(checks)
    result = HealthCheckResult(
        status=status,
        checked_at=checked_at,
        reason=reason,
        checks=checks,
        correlation_id=correlation_id,
    )
    if emit_transition:
        emit_health_transition(result)
    return result


def emit_health_transition(result: HealthCheckResult) -> None:
    global _previous_health_status
    previous = _previous_health_status
    if previous != result.status:
        evidence = DiagnosticEvidence(
            event="health_state_changed",
            previous_status=previous,
            current_status=result.status,
            reason=result.reason,
            correlation_id=result.correlation_id,
            occurred_at=result.checked_at,
        )
        logger.info(evidence.log_message())
    _previous_health_status = result.status


def reset_transition_state() -> None:
    global _previous_health_status
    _previous_health_status = None
