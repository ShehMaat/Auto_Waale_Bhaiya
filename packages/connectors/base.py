import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx


class JobSourceConnector(ABC):
    def __init__(self, timeout: int = 30, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=timeout)
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    async def search(self, query: str, **kwargs: Any) -> Any:
        pass

    @abstractmethod
    async def fetch(self, job_id: str) -> Any:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    async def _safe_fetch(self, url: str) -> httpx.Response:
        return await self._safe_fetch_with_redirects(url, method="GET")

    async def _safe_fetch_post(
        self, url: str, json_payload: dict[str, Any] | None = None
    ) -> httpx.Response:  # noqa: E501
        return await self._safe_fetch_with_redirects(url, method="POST", json_payload=json_payload)

    async def _safe_fetch_with_redirects(
        self,
        url: str,
        method: str,
        json_payload: dict[str, Any] | None = None,
        max_redirects: int = 3,  # noqa: E501
    ) -> httpx.Response:
        import asyncio
        import ipaddress
        import socket
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            raise ValueError("Invalid URL")

        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        addr_info = await asyncio.get_running_loop().getaddrinfo(
            host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
        )

        valid_ips = []
        for _family, type_, _proto, _canonname, sockaddr in addr_info:  # noqa: B007
            ip = ipaddress.ip_address(sockaddr[0])
            if not ip.is_loopback and not ip.is_private and not ip.is_link_local:
                valid_ips.append(ip)

        if not valid_ips:
            raise ValueError(f"SSRF blocked: No safe IPs found for {host}")

        request = self.client.build_request(method, url, json=json_payload)
        response = await self.client.send(request, follow_redirects=True)
        return response
