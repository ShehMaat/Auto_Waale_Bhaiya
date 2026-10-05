import socket
from typing import Any
from unittest.mock import patch

import pytest

from packages.connectors.base import JobSourceConnector


class DummyConnector(JobSourceConnector):
    def __init__(self) -> None:
        super().__init__()

    async def search(self, query: str, **kwargs: Any) -> Any:
        pass

    async def fetch(self, job_id: str) -> Any:
        pass

    async def health_check(self) -> bool:
        return True


def mock_getaddrinfo(ip: str) -> Any:
    async def _mock(*args: Any, **kwargs: Any) -> Any:
        # returns [(family, type, proto, canonname, sockaddr)]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]

    return _mock


@pytest.mark.asyncio
async def test_ssrf_direct_block_localhost() -> None:
    connector = DummyConnector()
    with patch("asyncio.BaseEventLoop.getaddrinfo", side_effect=mock_getaddrinfo("127.0.0.1")):
        with pytest.raises(ValueError, match="SSRF blocked: No safe IPs found"):
            await connector._safe_fetch("http://localhost")


@pytest.mark.asyncio
async def test_ssrf_direct_block_private() -> None:
    connector = DummyConnector()
    with patch("asyncio.BaseEventLoop.getaddrinfo", side_effect=mock_getaddrinfo("192.168.1.1")):
        with pytest.raises(ValueError, match="SSRF blocked: No safe IPs found"):
            await connector._safe_fetch("http://my-internal-service")


@pytest.mark.asyncio
async def test_ssrf_direct_block_link_local() -> None:
    connector = DummyConnector()
    with patch(
        "asyncio.BaseEventLoop.getaddrinfo", side_effect=mock_getaddrinfo("169.254.169.254")
    ):  # noqa: E501
        with pytest.raises(ValueError, match="SSRF blocked: No safe IPs found"):
            await connector._safe_fetch("http://169.254.169.254")


@pytest.mark.asyncio
async def test_ssrf_allow_public() -> None:
    connector = DummyConnector()
    with patch("asyncio.BaseEventLoop.getaddrinfo", side_effect=mock_getaddrinfo("93.184.216.34")):
        # The connection will fail because the mock backend actually tries to connect
        # but we just want to ensure it doesn't raise the SSRF ValueError.
        try:
            await connector._safe_fetch("http://example.com")
        except ValueError as e:
            if "SSRF blocked" in str(e):
                pytest.fail("SSRF raised incorrectly for public IP")
        except Exception:
            pass  # It's fine if the connection fails (e.g. ConnectError)
