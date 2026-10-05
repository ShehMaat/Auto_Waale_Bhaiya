import uuid

import pytest

from packages.browser.manager import BrowserManager
from packages.db.session import SessionLocal


@pytest.mark.asyncio
async def test_browser(db_session):
    from packages.db.models.candidate import User
    u_id = uuid.uuid4()
    db_session.add(User(id=u_id, email=f"{u_id}@example.com", hashed_password="pw"))
    db_session.commit()
    bm = BrowserManager()
    session = await bm.create_session(user_id=u_id, db_session=db_session, target_domain='example.com')
    page = await session.new_page()
    print('SUCCESS')
    await bm.stop()
