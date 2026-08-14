"""Operational visibility schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AvailabilityState(str, Enum):
    """Service availability state."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ServiceHealth(BaseModel):
    """Health status of an individual service."""

    service_name: str = Field(..., description="The name of the monitored service")
    status: str = Field(..., description="A human-readable status string")
    availability_state: AvailabilityState = Field(
        ..., description="The computed availability state"
    )
    latency_ms: float | None = Field(None, description="P95 latency in milliseconds, if available")
    last_evaluated_timestamp: datetime = Field(
        ..., description="When the status was last evaluated"
    )


class AlertClassification(str, Enum):
    """Operational alert classification."""

    BUSINESS = "business"
    APPLICATION = "application"
    INFRASTRUCTURE = "infrastructure"


class OperationalAlert(BaseModel):
    """A safe operational alert for executive visibility."""

    alert_type: str = Field(
        ...,
        description="The type of alert, e.g. 'service_unavailable', 'elevated_error_condition'",
    )
    classification: AlertClassification = Field(..., description="Alert classification")
    message: str = Field(..., description="Safe, human-readable alert message")
    service_name: str | None = Field(None, description="The affected service, if applicable")
    active_since: datetime | None = Field(None, description="When the alert became active")


class SystemPerformanceSummary(BaseModel):
    """Concise executive-level system performance summary."""

    api_availability: float | None = Field(
        None, description="Overall API availability percentage (0-100)"
    )
    overall_request_rate: float | None = Field(None, description="Overall requests per second")
    overall_error_rate: float | None = Field(None, description="Overall 5xx errors per second")
    healthy_service_count: int = Field(..., description="Number of fully healthy services")
    degraded_service_count: int = Field(..., description="Number of degraded services")
    unavailable_service_count: int = Field(..., description="Number of unavailable services")


class ExecutiveOperationsDashboard(BaseModel):
    """Complete operational visibility dashboard response."""

    services_health: list[ServiceHealth] = Field(
        ..., description="Health status of all monitored services"
    )
    active_alerts: list[OperationalAlert] = Field(
        ..., description="Currently active operational alerts"
    )
    system_performance: SystemPerformanceSummary = Field(
        ..., description="Executive system performance summary"
    )
    evaluated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the dashboard was compiled"
    )
