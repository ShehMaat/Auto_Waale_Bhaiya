from typing import Any, Dict, List

from packages.connectors.base import JobSourceConnector


class LeverConnector(JobSourceConnector):
    def __init__(self, site_name: str, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(**kwargs)
        self.site_name = site_name
        self.base_url = f"https://api.lever.co/v0/postings/{site_name}"

    async def search(self, query: str = "", **kwargs) -> List[Dict[str, Any]]:  # type: ignore[no-untyped-def]
        response = await self._safe_fetch(self.base_url)
        jobs = response.json()
        if query:
            jobs = [j for j in jobs if query.lower() in j.get("text", "").lower()]
        return jobs  # type: ignore[no-any-return]

    async def fetch(self, job_id: str) -> Dict[str, Any]:
        response = await self._safe_fetch(f"{self.base_url}/{job_id}")
        return response.json()  # type: ignore[no-any-return]

    async def health_check(self) -> bool:
        try:
            response = await self._safe_fetch(self.base_url)
            return response.status_code == 200
        except Exception:
            return False
