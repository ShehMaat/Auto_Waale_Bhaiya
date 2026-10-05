from playwright.sync_api import sync_playwright


def test_playwright_launch() -> None:  # type: ignore[no-untyped-def]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        assert page is not None
        browser.close()
