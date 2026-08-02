import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


SCREENSHOT_DIR = Path(os.environ.get("EXPERIMENT_FORGE_SCREENSHOT_DIR", "/tmp/experiment-forge-screens"))
BASE_URL = os.environ.get("EXPERIMENT_FORGE_BASE_URL", "http://127.0.0.1:8765")
APP_PATH = os.environ.get("EXPERIMENT_FORGE_APP_PATH", "/web/")


def app_url(query: str = "") -> str:
    path = APP_PATH if APP_PATH.startswith("/") else f"/{APP_PATH}"
    url = f"{BASE_URL.rstrip('/')}{path}"
    return f"{url}?{query}" if query else url


def test_decision_desk_critical_browser_path():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    request_failures: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("requestfailed", lambda request: request_failures.append(f"{request.url}: {request.failure}"))

        page.goto(app_url(), wait_until="networkidle")
        expect(page).to_have_title("Experiment Forge · Decision Desk")
        expect(page.locator("#landing-view")).to_be_visible()
        expect(page.locator("[data-workspace='checkout_progress_indicator']")).to_be_visible()
        page.screenshot(path=str(SCREENSHOT_DIR / "landing.png"), full_page=True)

        page.locator("[data-workspace='checkout_progress_indicator']").click()
        expect(page.locator("#workspace-view")).to_be_visible()
        expect(page.locator("#workspace-view h1")).to_contain_text("Checkout progress indicator")
        expect(page.locator(".decision-word")).to_have_text("investigate")
        expect(page.locator(".quality-summary .quality-pill").nth(3).locator("strong")).to_have_text("4")
        expect(page.locator(".check-name").filter(has_text="duplicate assignments")).to_be_visible()
        page.screenshot(path=str(SCREENSHOT_DIR / "investigate-workspace.png"), full_page=True)

        page.select_option("#workspace-select", "search_autocomplete_refresh")
        expect(page.locator("#workspace-view h1")).to_contain_text("Search autocomplete refresh")
        expect(page.locator(".decision-word")).to_have_text("launch")
        expect(page.locator(".quality-summary .quality-pill").nth(3).locator("strong")).to_have_text("0")
        page.locator(".methodology summary").click()
        expect(page.locator(".methodology-body")).to_be_visible()

        page.locator("#csv-file").set_input_files({
            "name": "invalid.csv",
            "mimeType": "text/csv",
            "buffer": b"user_id,variant\n1,control\n",
        })
        expect(page.locator("#validation-result")).to_contain_text("Missing")

        page.locator("#csv-file").set_input_files({
            "name": "raw_experiment_assignments.csv",
            "mimeType": "text/csv",
            "buffer": b"assignment_id,experiment_name,user_id,variant,assigned_at\n1,demo,1,control,2026-03-01 00:00:00\n",
        })
        expect(page.locator("#validation-result")).to_contain_text("Schema looks valid")
        page.screenshot(path=str(SCREENSHOT_DIR / "launch-workspace.png"), full_page=True)

        page.goto(app_url("experiment=checkout_progress_indicator"), wait_until="networkidle")
        expect(page.locator("#workspace-view h1")).to_contain_text("Checkout progress indicator")
        expect(page.locator(".decision-word")).to_have_text("investigate")

        browser.close()

    assert console_errors == []
    assert request_failures == []
