"""Small credential-safe HTTP client built only from the Python standard library."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class IntegrationTransportError(RuntimeError):
    """Report endpoint availability failure without including request credentials."""


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8")) if self.body else None

    def safe_body(self) -> str:
        return self.body.decode("utf-8", errors="replace")[:1000]


class HttpClient:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    def request(
        self,
        method: str,
        url: str,
        *,
        token: str | None = None,
        json_body: Any | None = None,
        form: dict[str, str] | None = None,
        request_id: str | None = None,
    ) -> HttpResponse:
        headers = {"Accept": "application/json"}
        data: bytes | None = None
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if request_id:
            headers["X-Request-ID"] = request_id
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif form is not None:
            data = urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        # Configuration validation restricts all endpoints to explicit HTTP(S) URLs.
        request = Request(url=url, data=data, headers=headers, method=method)  # noqa: S310
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:  # noqa: S310
                return HttpResponse(
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=response.read(),
                )
        except HTTPError as error:
            return HttpResponse(
                status=error.code,
                headers=dict(error.headers.items()),
                body=error.read(),
            )
        except URLError as error:
            raise IntegrationTransportError(
                f"The configured integration endpoint is unreachable: {url}"
            ) from error


def assert_status(response: HttpResponse, expected: int) -> None:
    assert response.status == expected, (
        f"Expected HTTP {expected}, received {response.status}. "
        f"Safe response body: {response.safe_body()}"
    )
