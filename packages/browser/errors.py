class BrowserError(Exception):
    """Base exception for all browser automation errors."""

    pass


class BrowserStartupError(BrowserError):
    """Raised when the browser or context fails to start."""

    pass


class BrowserSessionError(BrowserError):
    """Raised for general session-level errors."""

    pass


class SessionNotFoundError(BrowserSessionError):
    pass


class SessionOwnershipError(BrowserSessionError):
    pass


class BrowserNavigationError(BrowserError):
    """Raised when navigation fails (e.g. invalid scheme, unresolvable host, crash)."""

    pass


class BrowserTimeoutError(BrowserError):
    """Raised when a browser operation exceeds configured timeouts."""

    pass


class BrowserPolicyViolation(BrowserError):
    """Raised when a strict security policy (e.g. forbidden origin, file:// protocol)
    is violated."""

    pass


class BrowserChallengeError(BrowserError):
    """Raised when a challenge (CAPTCHA, OTP, 2FA) is detected and automation
    must pause or abort."""

    pass


class BrowserDownloadError(BrowserError):
    """Raised when a file download fails or violates security policy
    (e.g. path traversal, size limit)."""

    pass


class BrowserUploadError(BrowserError):
    """Raised when a file upload fails or violates security policy."""

    pass


class BrowserClosedError(BrowserError):
    """Raised when attempting to interact with a closed browser or page."""

    pass


class StaleSnapshotError(BrowserError):
    pass


class ActionValidationError(BrowserError):
    pass


class ElementNotFoundError(BrowserError):
    pass


class ElementAmbiguousError(BrowserError):
    pass


class SensitiveActionBlockedError(BrowserError):
    pass


class ResourceLimitError(BrowserError):
    pass


class SubmissionBlockedError(BrowserError):
    pass


class RecoveryError(BrowserError):
    pass
