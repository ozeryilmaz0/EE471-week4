"""Browser end-to-end test for DreamCanvas AI using Playwright + the installed Chrome.

The microphone is replaced by Chrome's fake capture device that plays
test_audio/hello.wav (created by test_api.py), so the full voice flow is tested:
mic -> /api/transcribe -> message box -> Send -> bot reply -> "Use as image prompt" -> Paint.

Screenshots are written to docs/ (desktop frame + mobile).

Usage (server running, from the repo root):
    venv\\Scripts\\python.exe MiniProject3\\test_ui.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:5000/"
HERE = Path(__file__).resolve().parent
WAV = HERE / "test_audio" / "hello.wav"
DOCS = HERE / "docs"

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}", flush=True)


def wait_for_bot_reply(page, count_before: int) -> str:
    page.wait_for_function(
        "n => document.querySelectorAll('.msg.bot:not(.typing)').length > n", arg=count_before, timeout=30000
    )
    return page.locator(".msg.bot:not(.typing) .text").last.inner_text()


def main() -> int:
    if not WAV.exists():
        print("Run test_api.py first to create test_audio/hello.wav")
        return 1
    DOCS.mkdir(exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                f"--use-file-for-fake-audio-capture={WAV}",
            ],
        )
        context = browser.new_context(viewport={"width": 1280, "height": 1000}, device_scale_factor=1)
        context.grant_permissions(["microphone"], origin=URL.rstrip("/"))
        page = context.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(URL)
        page.wait_for_load_state("networkidle")
        box = page.locator("#app").bounding_box()
        check("layout: phone frame is 430x932", round(box["width"]) == 430 and round(box["height"]) == 932, str(box))
        img_box = page.locator("#imageBox").bounding_box()
        check("layout: image box is 390x390", round(img_box["width"]) == 390 and round(img_box["height"]) == 390, str(img_box))
        page.locator("#app").screenshot(path=str(DOCS / "screenshot_empty.png"))

        # Empty prompt -> toast with the server's / client's error
        page.click("#paintBtn")
        toast = page.locator("#toast")
        check("paint: empty prompt shows error", toast.is_visible() and "prompt" in toast.inner_text().lower(), toast.inner_text())

        # Voice: record ~4.5 s from the fake mic, then stop
        page.click("#micBtn")
        page.wait_for_selector("#micBtn.recording", timeout=5000)
        recording = True
        time.sleep(4.5)
        page.click("#micBtn")
        t = time.perf_counter()
        page.wait_for_function("document.getElementById('messageInput').value.trim().length > 0", timeout=30000)
        said = page.input_value("#messageInput")
        check("mic: records and transcribes", recording and "draw a picture" in said.lower(),
              f"{time.perf_counter() - t:.2f}s -> {said}")

        # Ask for a prompt (replace the transcript so the reply is predictable)
        page.fill("#messageInput", "Hi! Can you give me a prompt for a cool digital painting?")
        bots = page.locator(".msg.bot:not(.typing)").count()
        page.click("#sendBtn")
        typing_seen = page.locator(".msg.typing").count() > 0
        t = time.perf_counter()
        reply = wait_for_bot_reply(page, bots)
        check("chat: typing indicator + reply", typing_seen and len(reply.split()) >= 5,
              f"{time.perf_counter() - t:.2f}s -> {reply}")

        page.locator(".msg.bot .use-prompt").last.click()
        check("chat: 'Use as image prompt' fills prompt box", page.input_value("#promptInput") == reply)

        t = time.perf_counter()
        page.click("#paintBtn")
        page.wait_for_selector("#resultImage:not([hidden])", timeout=60000)
        check("paint: image shown + download button", page.locator("#downloadBtn").is_visible(),
              f"{time.perf_counter() - t:.2f}s, chip '{page.inner_text('#infoChip')}'")

        page.fill("#messageInput", "Wow, I love it!")
        bots = page.locator(".msg.bot:not(.typing)").count()
        page.press("#messageInput", "Enter")
        reply2 = wait_for_bot_reply(page, bots)
        check("chat: Enter sends a second turn", bool(reply2), reply2)
        page.wait_for_timeout(600)
        page.locator("#app").screenshot(path=str(DOCS / "screenshot.png"))

        # Mobile viewport
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                     is_mobile=True, has_touch=True)
        mpage = mobile.new_page()
        mpage.goto(URL)
        mpage.wait_for_load_state("networkidle")
        overflow = mpage.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        check("mobile: no horizontal overflow", not overflow)
        mpage.screenshot(path=str(DOCS / "screenshot_mobile.png"))
        browser.close()

    check("browser console: no errors", not errors, "; ".join(errors[:3]))
    passed = sum(ok for _, ok, _ in checks)
    print(f"\n{passed}/{len(checks)} UI checks passed. Screenshots in {DOCS}")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
