"""Application-safe errors translated by the HTTP boundary."""


class ApplicationError(Exception):
    """Base class for expected application failures."""

    status_code = 500
    code = "application_error"
    message = "The request could not be completed."


class AuthenticationError(ApplicationError):
    status_code = 401
    code = "authentication_required"
    message = "Valid authentication is required."


class AuthorizationError(ApplicationError):
    status_code = 403
    code = "forbidden"
    message = "You are not authorized to perform this action."


class ResourceNotFoundError(ApplicationError):
    status_code = 404
    code = "not_found"
    message = "The requested resource was not found."


class ConflictError(ApplicationError):
    status_code = 409
    code = "conflict"
    message = "The request conflicts with the current resource state."


class DependencyUnavailableError(ApplicationError):
    status_code = 503
    code = "dependency_unavailable"
    message = "A required service dependency is unavailable."
