from pathlib import Path

from packages.browser.errors import BrowserPolicyViolation
from packages.browser.policies import BrowserSecurityPolicy


class BrowserDownloadManager:
    """Manages secure file downloads from the browser."""

    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir).resolve()
        # Ensure the download directory exists and is safe
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def secure_save(self, filename: str, content: bytes) -> str:
        """Validates and securely saves a downloaded file."""
        BrowserSecurityPolicy.validate_download(filename, len(content))

        target_path = (self.download_dir / filename).resolve()

        # Prevent path traversal outside the download dir
        if not target_path.is_relative_to(self.download_dir):
            raise BrowserPolicyViolation("Path traversal detected in download save")

        with open(target_path, "wb") as f:
            f.write(content)

        return str(target_path)
