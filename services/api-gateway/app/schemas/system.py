"""Schemas for foundation endpoints."""

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Non-sensitive process or dependency health status."""

    model_config = ConfigDict(extra="forbid")

    status: str
    service: str
    version: str


class ServiceInfoResponse(BaseModel):
    """Non-sensitive service metadata."""

    model_config = ConfigDict(extra="forbid")

    service: str
    version: str
    environment: str
