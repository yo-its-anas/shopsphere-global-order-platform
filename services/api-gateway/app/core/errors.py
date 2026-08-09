"""Safe gateway errors translated at the HTTP boundary."""


class GatewayError(Exception):
    """Base class for expected upstream failures."""

    status_code = 502
    code = "upstream_error"
    message = "The upstream service could not complete the request."


class UpstreamTimeoutError(GatewayError):
    status_code = 504
    code = "upstream_timeout"
    message = "The upstream service did not respond in time."


class UpstreamUnavailableError(GatewayError):
    status_code = 503
    code = "upstream_unavailable"
    message = "The requested capability is temporarily unavailable."
