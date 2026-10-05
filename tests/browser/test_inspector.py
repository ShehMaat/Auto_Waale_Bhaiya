from unittest.mock import AsyncMock

import pytest

from packages.browser.inspector import PageInspector


@pytest.mark.asyncio
async def test_page_inspector() -> None:
    mock_page = AsyncMock()

    # Simulate Playwright returning a raw javascript list
    mock_page._page.evaluate.return_value = [
        {
            "element_id": "el-0",
            "tag_name": "button",
            "is_visible": True,
            "is_interactive": True,
            "text": "Submit",
            "input_type": None,
            "role": "button",
            "aria_label": None,
        },
        {
            "element_id": "el-1",
            "tag_name": "input",
            "is_visible": True,
            "is_interactive": True,
            "text": "",
            "input_type": "text",
            "role": None,
            "aria_label": "Email",
        },
    ]

    mock_page.get_url.return_value = "https://example.com"
    mock_page.get_title.return_value = "Example Title"

    inspector = PageInspector()
    model = await inspector.inspect(mock_page)

    assert model.url == "https://example.com"
    assert model.title == "Example Title"
    assert len(model.elements) == 2

    btn = model.elements[0]
    assert btn.element_id == "el-0"
    assert btn.metadata.tag_name == "button"
    assert btn.metadata.text == "Submit"

    inp = model.elements[1]
    assert inp.element_id == "el-1"
    assert inp.metadata.input_type == "text"
    assert inp.metadata.aria_label == "Email"
