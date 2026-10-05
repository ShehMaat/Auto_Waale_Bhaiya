from urllib.parse import urlparse

from packages.browser.errors import BrowserPolicyViolation
from packages.config.settings import settings


class BrowserSecurityPolicy:
    """Centralized security policy for browser automation."""

    ALLOWED_SCHEMES = {"http", "https"}
    BLOCKED_HOSTS = {
        "127.0.0.1",
        "localhost",
        "169.254.169.254",  # AWS Metadata
        "::1",
    }

    @classmethod
    def validate_navigation_url(cls, url: str) -> str:
        """Validates that a URL is safe for navigation."""
        if not url:
            raise BrowserPolicyViolation("URL cannot be empty")

        try:
            parsed = urlparse(url)
        except Exception as e:
            raise BrowserPolicyViolation(f"Invalid URL format: {str(e)}") from e

        # 1. Scheme Validation
        if parsed.scheme.lower() not in cls.ALLOWED_SCHEMES:
            raise BrowserPolicyViolation(f"Blocked dangerous scheme: {parsed.scheme}")

        # 2. Host Validation
        host = parsed.hostname
        if not host:
            raise BrowserPolicyViolation("URL must contain a hostname")

        if host.lower() in cls.BLOCKED_HOSTS:
            raise BrowserPolicyViolation(f"Navigation to blocked host: {host}")

        # Note: True DNS rebinding protection and private IP blocking requires
        # intercepting Playwright's network layer or routing traffic through a Safe Proxy.
        # This basic check prevents trivial local SSRF attempts in Playwright navigation.

        # 3. Target Domain Validation (if BROWSER_ALLOWED_ORIGINS is configured)
        if settings.BROWSER_ALLOWED_ORIGINS:
            is_allowed = False
            for allowed_origin in settings.BROWSER_ALLOWED_ORIGINS:
                host_lower = host.lower()
                origin_lower = allowed_origin.lower()
                if host_lower == origin_lower or host_lower.endswith(f".{origin_lower}"):
                    is_allowed = True
                    break

            if not is_allowed:
                raise BrowserPolicyViolation(f"Navigation to unauthorized origin: {host}")

        return url

    @classmethod
    def validate_download(cls, filename: str, file_size: int) -> None:
        """Validates download parameters."""
        if file_size > (settings.BROWSER_MAX_DOWNLOAD_MB * 1024 * 1024):
            raise BrowserPolicyViolation(
                f"Download exceeds maximum allowed size ({settings.BROWSER_MAX_DOWNLOAD_MB}MB)"
            )

        if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
            raise BrowserPolicyViolation("Path traversal detected in download filename")

    @classmethod
    def validate_upload(cls, file_size: int) -> None:
        """Validates upload parameters."""
        if file_size > (settings.BROWSER_MAX_UPLOAD_MB * 1024 * 1024):
            raise BrowserPolicyViolation(
                f"Upload exceeds maximum allowed size ({settings.BROWSER_MAX_UPLOAD_MB}MB)"
            )
