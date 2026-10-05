from pathlib import Path

import pytest

from packages.browser.downloads import BrowserDownloadManager
from packages.browser.errors import BrowserPolicyViolation


def test_download_security_path_traversal(tmp_path) -> None:
    manager = BrowserDownloadManager(str(tmp_path))

    # Valid download
    safe_path = manager.secure_save("resume.pdf", b"content")
    assert Path(safe_path).parent == tmp_path

    # Path traversal attempts
    with pytest.raises(BrowserPolicyViolation, match="Path traversal detected"):
        manager.secure_save("../secret.txt", b"content")

    with pytest.raises(BrowserPolicyViolation, match="Path traversal detected"):
        manager.secure_save("../../etc/passwd", b"content")

    # Absolute paths are blocked if they escape the directory
    import os

    if os.name == "nt":
        unsafe_absolute = "C:\\Windows\\System32\\cmd.exe"
    else:
        unsafe_absolute = "/etc/shadow"

    with pytest.raises(BrowserPolicyViolation):
        manager.secure_save(unsafe_absolute, b"content")


def test_download_security_max_size(tmp_path) -> None:
    manager = BrowserDownloadManager(str(tmp_path))

    # BROWSER_MAX_DOWNLOAD_MB is 50
    large_content = b"a" * (51 * 1024 * 1024)
    with pytest.raises(BrowserPolicyViolation):
        manager.secure_save("large.pdf", large_content)
