def _browser_sign_in(page, live_server, email="admin@example.test"):
    page.goto(f"{live_server}/sign-in")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill("correct-password")
    page.get_by_role("button", name="Sign in").click()


def test_admin_monitoring_responsive_layout_and_focus(browser, live_server):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    _browser_sign_in(page, live_server)

    page.goto(f"{live_server}/admin/monitoring")

    assert page.get_by_role("heading", name="Health monitoring").is_visible()
    assert page.locator(".summary-grid").first.is_visible()
    assert page.get_by_text("Recommended action").first.is_visible()
    assert page.get_by_text("Storage").first.is_visible()
    assert page.get_by_text("Identity workflows").first.is_visible()
    assert page.get_by_role("link", name="Monitoring").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement !== document.body")
    page.close()


def test_non_admin_cannot_see_monitoring_indicators_in_browser(browser, live_server):
    page = browser.new_page()
    _browser_sign_in(page, live_server, email="member@example.test")

    page.goto(f"{live_server}/admin/monitoring")

    assert page.get_by_text("Administrator access required").is_visible()
    assert page.get_by_text("Service catalog").count() == 0
    assert page.get_by_text("Recommended action").count() == 0
    page.close()
