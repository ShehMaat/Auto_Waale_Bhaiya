import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from packages.browser.executor import ActionExecutor
from packages.schemas.browser_actions import ClickAction


@pytest.mark.asyncio
async def test_action_executor_idempotency() -> None:
    mock_db = MagicMock()
    mock_page = AsyncMock()
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()

    # Mock session
    class MockSessionRecord:
        state = "ACTIVE"

    MockSessionRecord.user_id = user_id

    mock_db.query().filter_by().first.return_value = MockSessionRecord()

    action = ClickAction(
        action_id="action_x", session_id=str(session_id), snapshot_id="123", element_id="btn"
    )

    # First execution succeeds
    # Ensure db.add doesn't raise exception
    mock_db.add = MagicMock()

    res1 = await ActionExecutor.execute(action, mock_page, mock_db, user_id)
    assert res1["status"] == "SUCCESS"
    mock_page.click_element.assert_called_once_with("btn")

    # Second execution raises IntegrityError on db.commit
    # We simulate this by changing the mock for db.add
    mock_db.add.side_effect = IntegrityError("fake", "fake", "fake")

    # Mock the query for previous result
    class MockPrevResult:
        result_json = {"status": "SUCCESS"}

    mock_db.query().filter_by().first.side_effect = [MockSessionRecord(), MockPrevResult()]

    mock_page.click_element.reset_mock()

    res2 = await ActionExecutor.execute(action, mock_page, mock_db, user_id)
    assert res2["status"] == "DUPLICATE"

    # Verify that the browser action was NOT executed again
    mock_page.click_element.assert_not_called()
