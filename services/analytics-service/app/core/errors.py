"""Application-safe errors translated at the HTTP boundary."""


class ApplicationError(Exception):
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
    message = "You are not authorized to access executive analytics."


class IdentityProviderUnavailableError(ApplicationError):
    status_code = 503
    code = "identity_provider_unavailable"
    message = "Identity verification is temporarily unavailable."
