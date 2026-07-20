"""Browser QA for the synchronized LAB3 dual-camera player."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:8132/arm-lab.html"
OUT_DIR = Path(__file__).resolve().parent / "out" / "arm-lab"


def assert_synchronized(summary: dict) -> None:
    assert summary["pass"], summary
    assert summary["schemaVersion"] == "physical-ai-public-arm-lab-v1", summary
    assert summary["frames"] > 0, summary
    assert summary["frame"] == summary["graphCursorFrame"], summary
    assert summary["syncDelta"] is not None and summary["syncDelta"] <= 0.08, summary
    assert "recorded" in summary["claimBoundary"].lower(), summary
    assert "simulation" in summary["claimBoundary"].lower(), summary
    assert summary["cameraContract"]["model_input"] == "observation.images.image", summary
    assert summary["cameraContract"]["observer_only"] == ["observation.images.image2"], summary


def wait_summary(page):
    page.wait_for_function("() => window.qaArmLabSummary?.().pass === true")
    return page.evaluate("window.qaArmLabSummary()")


def run_desktop(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 1080})
    console_errors: list[str] = []
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: console_errors.append(str(error)))
    page.goto(BASE_URL, wait_until="networkidle")
    page.get_by_role("heading", name="로봇이 보고, 움직이고, 결과를 만든 기록").wait_for()
    summary = wait_summary(page)
    assert summary["episode"] == "pass", summary
    assert summary["frames"] == 78, summary
    assert_synchronized(summary)

    slider = page.locator('input[type="range"]')
    slider.fill("3")
    page.wait_for_function("() => Math.abs(window.qaArmLabSummary().currentTime - 3) < 0.06")
    summary = page.evaluate("window.qaArmLabSummary()")
    assert summary["frame"] == 30, summary
    assert_synchronized(summary)

    page.get_by_role("button", name="실패 기록 FAIL").click()
    page.wait_for_function("() => window.qaArmLabSummary?.().episode === 'fail' && window.qaArmLabSummary().frames === 220")
    fail_summary = page.evaluate("window.qaArmLabSummary()")
    assert fail_summary["outcome"]["success"] is False, fail_summary
    assert fail_summary["outcome"]["termination"] == "timeout", fail_summary
    assert_synchronized(fail_summary)

    page.locator("body").click(position={"x": 20, "y": 20})
    page.keyboard.press("ArrowRight")
    page.wait_for_function("() => window.qaArmLabSummary().frame === 1")
    keyboard_summary = page.evaluate("window.qaArmLabSummary()")
    assert_synchronized(keyboard_summary)

    negative_summary = page.evaluate(
        """() => {
          const wrist = document.querySelector('[data-testid="wrist-camera"] video');
          wrist.currentTime = window.qaArmLabSummary().mainTime + 0.75;
          return window.qaArmLabSummary();
        }"""
    )
    negative_probe_passed = False
    try:
        assert_synchronized(negative_summary)
    except AssertionError:
        negative_probe_passed = True
    assert negative_probe_passed, negative_summary
    page.locator('[data-testid="main-camera"] video').dispatch_event("timeupdate")
    page.wait_for_function("() => window.qaArmLabSummary().syncDelta <= 0.08")

    page.screenshot(path=OUT_DIR / "desktop.png", full_page=True)
    assert not console_errors, console_errors
    page.close()
    return {"summary": keyboard_summary, "negativeDesyncRejected": negative_probe_passed, "consoleErrors": console_errors}


def run_mobile(browser):
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
    page.goto(BASE_URL, wait_until="networkidle")
    summary = wait_summary(page)
    assert_synchronized(summary)
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 0, {"horizontalOverflow": overflow}
    assert page.get_by_test_id("main-camera").bounding_box()["y"] < page.get_by_test_id("wrist-camera").bounding_box()["y"]
    page.screenshot(path=OUT_DIR / "mobile.png", full_page=True)
    page.close()
    return {"horizontalOverflow": overflow, "sourceOrderStable": True}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        report = {
            "desktop": run_desktop(browser),
            "mobile": run_mobile(browser),
        }
        browser.close()
    report["pass"] = True
    (OUT_DIR / "player-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
