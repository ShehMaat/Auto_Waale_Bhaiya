from typing import Any

import pytest

from packages.browser.downloads import BrowserDownloadManager
from packages.browser.errors import BrowserPolicyViolation
from packages.browser.policies import BrowserSecurityPolicy


def test_dangerous_schemes_blocked() -> None:
    with pytest.raises(BrowserPolicyViolation, match="Blocked dangerous scheme"):
        BrowserSecurityPolicy.validate_navigation_url("file:///etc/passwd")

    with pytest.raises(BrowserPolicyViolation, match="Blocked dangerous scheme"):
        BrowserSecurityPolicy.validate_navigation_url("javascript:alert(1)")

    with pytest.raises(BrowserPolicyViolation, match="Blocked dangerous scheme"):
        BrowserSecurityPolicy.validate_navigation_url("data:text/html,<h1>test</h1>")


def test_blocked_hosts() -> None:
    with pytest.raises(BrowserPolicyViolation, match="Navigation to blocked host"):
        BrowserSecurityPolicy.validate_navigation_url("http://127.0.0.1/admin")

    with pytest.raises(BrowserPolicyViolation, match="Navigation to blocked host"):
        BrowserSecurityPolicy.validate_navigation_url("http://localhost:8000/")

    with pytest.raises(BrowserPolicyViolation, match="Navigation to blocked host"):
        BrowserSecurityPolicy.validate_navigation_url("http://169.254.169.254/latest/meta-data")


def test_safe_navigation() -> None:
    url = "https://www.google.com/search?q=test"
    assert BrowserSecurityPolicy.validate_navigation_url(url) == url


def test_download_path_traversal(tmp_path: Any) -> None:
    manager = BrowserDownloadManager(str(tmp_path))

    with pytest.raises(BrowserPolicyViolation, match="Path traversal detected"):
        manager.secure_save("../../etc/passwd", b"content")

    with pytest.raises(BrowserPolicyViolation, match="Path traversal detected"):
        manager.secure_save("/absolute/path/test.txt", b"content")


def test_download_size_limit(monkeypatch: Any, tmp_path: Any) -> None:
    # Mock settings max limit to 1MB
    monkeypatch.setattr("packages.browser.policies.settings.BROWSER_MAX_DOWNLOAD_MB", 1)
    manager = BrowserDownloadManager(str(tmp_path))

    with pytest.raises(BrowserPolicyViolation, match="Download exceeds maximum allowed size"):
        manager.secure_save("big_file.bin", b"0" * (1024 * 1024 + 1))
