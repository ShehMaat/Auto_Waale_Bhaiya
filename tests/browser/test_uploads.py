import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from packages.browser.executor import ActionExecutor
from packages.schemas.browser_actions import UploadFileAction


class MockDocument:
    def __init__(self, id, user_id, storage_key, file_size):
        self.id = id
        self.user_id = user_id
        self.storage_key = storage_key
        self.file_size = file_size


@pytest.mark.asyncio
async def test_cross_user_upload() -> None:
    # Setup
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    mock_db = MagicMock()
    mock_page = AsyncMock()

    # Document belongs to user B
    doc = MockDocument(id=uuid.uuid4(), user_id=user_b, storage_key="test.pdf", file_size=1000)

    # Mock DB query
    # first() will return the BrowserSessionModel or Document depending on the call.
    # executor.py queries BrowserSessionModel FIRST, then Document.
    # Let's mock the session check to pass.
    class MockSession:
        user_id = user_a
        state = "ACTIVE"

    def side_effect(model):
        m = MagicMock()
        if model.__name__ == "BrowserSessionModel":
            m.filter_by.return_value.first.return_value = MockSession()
        elif model.__name__ == "BrowserActionExecutionModel":
            m.filter_by.return_value.first.return_value = None
        else:
            m.filter_by.return_value.first.return_value = doc
        return m

    mock_db.query.side_effect = side_effect

    action = UploadFileAction(
        action_id="1",
        session_id=str(uuid.uuid4()),
        snapshot_id="123",
        element_id="upload_btn",
        document_id=str(doc.id),
    )

    with pytest.raises(PermissionError, match="Document not found or unauthorized."):
        await ActionExecutor.execute(action, mock_page, mock_db, user_id=user_a)


@pytest.mark.asyncio
async def test_oversized_upload() -> None:
    # Setup
    user_a = uuid.uuid4()

    mock_db = MagicMock()
    mock_page = AsyncMock()

    doc = MockDocument(
        id=uuid.uuid4(), user_id=user_a, storage_key="test.pdf", file_size=20 * 1024 * 1024
    )

    class MockSession:
        user_id = user_a
        state = "ACTIVE"

    def side_effect(model):
        m = MagicMock()
        if model.__name__ == "BrowserSessionModel":
            m.filter_by.return_value.first.return_value = MockSession()
        elif model.__name__ == "BrowserActionExecutionModel":
            m.filter_by.return_value.first.return_value = None
        else:
            m.filter_by.return_value.first.return_value = doc
        return m

    mock_db.query.side_effect = side_effect

    action = UploadFileAction(
        action_id="1",
        session_id=str(uuid.uuid4()),
        snapshot_id="123",
        element_id="upload_btn",
        document_id=str(doc.id),
    )

    with pytest.raises(ValueError, match="File exceeds maximum allowed upload size."):
        await ActionExecutor.execute(action, mock_page, mock_db, user_id=user_a)
