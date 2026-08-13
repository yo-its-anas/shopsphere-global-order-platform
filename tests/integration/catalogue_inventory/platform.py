"""Credential-safe, explicitly enabled Kubernetes observations and outage controls."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from typing import Any


class PlatformInspectionError(RuntimeError):
    """Report a platform inspection failure without exposing pod environment values."""


_OUTBOX_QUERY = r"""
import asyncio, json, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text('''
                SELECT event_type, event_version, aggregate_type,
                       aggregate_id::text, correlation_id, producer, payload,
                       status, attempts, published_at IS NOT NULL AS published
                  FROM domain_event_outbox
                 WHERE correlation_id = :correlation_id
                 ORDER BY occurred_at
            '''), {"correlation_id": os.environ["TEST_CORRELATION_ID"]})
            print(json.dumps([dict(row._mapping) for row in result]))
    finally:
        await engine.dispose()
asyncio.run(main())
"""


@dataclass(slots=True)
class PlatformInspector:
    context: str

    def _run(self, arguments: list[str], timeout: int = 60) -> str:
        command = ["kubectl", "--context", self.context, *arguments]
        try:
            result = subprocess.run(  # noqa: S603
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise PlatformInspectionError(
                "A Kubernetes platform check failed; inspect cluster events separately."
            ) from error
        return result.stdout

    def cache_log_count(self, event: str, family: str) -> int:
        output = self._run(
            [
                "-n",
                "shopsphere-apps",
                "logs",
                "deployment/catalogue-service",
                "-c",
                "catalogue-service",
                "--since=10m",
            ]
        )
        return sum(
            event in line and f'"cache_family":"{family}"' in line
            for line in output.splitlines()
        )

    def outbox_events(self, correlation_id: str) -> list[dict[str, Any]]:
        output = self._run(
            [
                "-n",
                "shopsphere-apps",
                "exec",
                "deployment/catalogue-service",
                "-c",
                "catalogue-service",
                "--",
                "env",
                f"TEST_CORRELATION_ID={correlation_id}",
                "python",
                "-c",
                _OUTBOX_QUERY,
            ]
        )
        document = json.loads(output)
        if not isinstance(document, list):
            raise PlatformInspectionError(
                "The safe outbox query returned an unexpected shape."
            )
        return document

    def wait_for_published(
        self, correlation_id: str, timeout_seconds: int = 30
    ) -> list[dict[str, Any]]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            events = self.outbox_events(correlation_id)
            if events and all(event["status"] == "published" for event in events):
                return events
            time.sleep(1)
        raise PlatformInspectionError(
            "Outbox events were not published within the bounded wait."
        )

    def scale(self, namespace: str, resource: str, replicas: int) -> None:
        self._run(["-n", namespace, "scale", resource, f"--replicas={replicas}"])

    def wait_for_ready_replicas(
        self,
        namespace: str,
        resource: str,
        replicas: int,
        timeout_seconds: int = 90,
    ) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            value = self._run(
                [
                    "-n",
                    namespace,
                    "get",
                    resource,
                    "-o",
                    "jsonpath={.status.readyReplicas}",
                ]
            ).strip()
            ready = int(value) if value else 0
            if ready == replicas:
                return
            time.sleep(1)
        raise PlatformInspectionError(
            "The controlled workload did not reach the requested replica state."
        )

    def wait_rollout(
        self, namespace: str, resource: str, timeout_seconds: int = 180
    ) -> None:
        self._run(
            [
                "-n",
                namespace,
                "rollout",
                "status",
                resource,
                f"--timeout={timeout_seconds}s",
            ],
            timeout=timeout_seconds + 10,
        )
