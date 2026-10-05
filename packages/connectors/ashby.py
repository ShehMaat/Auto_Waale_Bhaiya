from typing import Any, Dict, List

from packages.connectors.base import JobSourceConnector


class AshbyConnector(JobSourceConnector):
    def __init__(self, board_name: str, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(**kwargs)
        self.board_name = board_name
        self.base_url = "https://api.ashbyhq.com/posting-api"

    async def search(self, query: str = "", **kwargs) -> List[Dict[str, Any]]:  # type: ignore[no-untyped-def]
        payload = {"jobBoardName": self.board_name}
        response = await self._safe_fetch_post(f"{self.base_url}/job-board/list", payload)
        jobs = response.json().get("jobs", [])
        if query:
            jobs = [j for j in jobs if query.lower() in j.get("title", "").lower()]
        return jobs  # type: ignore[no-any-return]

    async def fetch(self, job_id: str) -> Dict[str, Any]:
        response = await self._safe_fetch(f"{self.base_url}/job/{job_id}")
        return response.json()  # type: ignore[no-any-return]

    async def health_check(self) -> bool:
        # Ashby requires POST for job-board list, just check if API domain is reachable
        try:
            response = await self._safe_fetch("https://api.ashbyhq.com")
            # 404 or 401 is fine, it means the server is up
            return response.status_code in [200, 401, 404]
        except Exception:
            return False
