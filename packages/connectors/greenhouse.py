from typing import Any, Dict, List

from packages.connectors.base import JobSourceConnector


class GreenhouseConnector(JobSourceConnector):
    def __init__(self, board_token: str, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(**kwargs)
        self.board_token = board_token
        self.base_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}"

    async def search(self, query: str = "", **kwargs) -> List[Dict[str, Any]]:  # type: ignore[no-untyped-def]
        response = await self._safe_fetch(f"{self.base_url}/jobs")
        jobs = response.json().get("jobs", [])
        if query:
            jobs = [j for j in jobs if query.lower() in j.get("title", "").lower()]
        return jobs  # type: ignore[no-any-return]

    async def fetch(self, job_id: str) -> Dict[str, Any]:
        response = await self._safe_fetch(f"{self.base_url}/jobs/{job_id}")
        return response.json()  # type: ignore[no-any-return]

    async def health_check(self) -> bool:
        try:
            response = await self._safe_fetch(self.base_url)
            return response.status_code == 200
        except Exception:
            return False
