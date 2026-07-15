"""
playwright_agent.py — Browser Hands
=====================================
Deep module for operating real websites using your already-authenticated
Chrome/Edge browser sessions. No logins needed — uses existing profiles.

Public interface (never raises):
  navigate(url, profile)              -> BrowserResult
  read_page_text(url, profile)        -> BrowserResult
  fill_and_submit_form(url, fields, submit_selector, profile) -> BrowserResult
  answer_and_submit_quiz(url, ai_answerer, profile)           -> BrowserResult
  take_screenshot(url, profile)       -> BrowserResult

Key design:
  - Uses launch_persistent_context() with real user profile → already logged in
  - Human-like timing (random delays) to avoid bot detection
  - Screenshots taken as evidence after every action
  - Falls back to headless=False (visible browser) for auths that need cookies
"""

import logging
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("jules_bridge.playwright_agent")

_ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
_SCREENSHOT_DIR = _ROOT_DIR / "memory" / "screenshots"
_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# --- Default Chrome profile path (Windows) ---
_DEFAULT_CHROME_PROFILE = os.environ.get(
    "PLAYWRIGHT_CHROME_PROFILE",
    r"C:\Users\shpctac1002c\AppData\Local\Google\Chrome\User Data"
)
_DEFAULT_EDGE_PROFILE = os.environ.get(
    "PLAYWRIGHT_EDGE_PROFILE",
    r"C:\Users\shpctac1002c\AppData\Local\Microsoft\Edge\User Data"
)
_SCREENSHOT_TIMEOUT = int(os.environ.get("PLAYWRIGHT_TIMEOUT_MS", "30000"))


@dataclass
class BrowserResult:
    ok: bool
    url: str = ""
    page_text: str = ""
    screenshot_path: str = ""
    form_submitted: bool = False
    quiz_answers: list = field(default_factory=list)
    error: Optional[str] = None
    timing_ms: int = 0


def _human_delay(min_ms: int = 200, max_ms: int = 800) -> None:
    """Random human-like delay to avoid bot detection."""
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


def _get_playwright_context(profile: Optional[str] = None, channel: str = "chrome"):
    """
    Launch a persistent browser context using an existing user profile.
    Returns (playwright_instance, context) — caller must stop playwright.
    """
    try:
        from playwright.sync_api import sync_playwright  # lazy import — headless-incompatible
    except ImportError as exc:
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"
        ) from exc

    user_data_dir = profile or _DEFAULT_CHROME_PROFILE

    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        channel=channel,
        headless=False,          # must be False to use existing auth cookies
        args=[
            "--disable-blink-features=AutomationControlled",  # hide automation
            "--no-first-run",
            "--no-default-browser-check",
        ],
        ignore_default_args=["--enable-automation"],
        timeout=_SCREENSHOT_TIMEOUT,
    )
    return playwright, context


def _save_screenshot(page, label: str) -> str:
    """Take a screenshot and return the saved path."""
    try:
        ts = int(time.time())
        path = _SCREENSHOT_DIR / f"{label}_{ts}.png"
        page.screenshot(path=str(path))
        return str(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Screenshot failed: %s", exc)
        return ""


def navigate(url: str, profile: Optional[str] = None) -> BrowserResult:
    """Navigate to URL and return page text + screenshot."""
    start = time.time()
    playwright = None
    try:
        playwright, context = _get_playwright_context(profile)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=_SCREENSHOT_TIMEOUT)
        _human_delay(500, 1200)
        text = page.inner_text("body") or ""
        shot = _save_screenshot(page, "navigate")
        context.close()
        return BrowserResult(
            ok=True, url=url, page_text=text[:8000], screenshot_path=shot,
            timing_ms=int((time.time() - start) * 1000)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("navigate failed: %s", exc)
        return BrowserResult(ok=False, url=url, error=str(exc),
                             timing_ms=int((time.time() - start) * 1000))
    finally:
        if playwright:
            try:
                playwright.stop()
            except Exception:  # noqa: BLE001
                pass


def read_page_text(url: str, profile: Optional[str] = None) -> BrowserResult:
    """Navigate and return full readable text (for research tasks)."""
    return navigate(url, profile)


def fill_and_submit_form(
    url: str,
    fields: dict,           # {selector: value} e.g. {"#name": "Abdul", "#email": "a@b.com"}
    submit_selector: str = "input[type=submit], button[type=submit]",
    profile: Optional[str] = None,
) -> BrowserResult:
    """Fill form fields and submit. Returns result with screenshot evidence."""
    start = time.time()
    playwright = None
    try:
        playwright, context = _get_playwright_context(profile)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=_SCREENSHOT_TIMEOUT)
        _human_delay(800, 1500)

        for selector, value in fields.items():
            try:
                page.wait_for_selector(selector, timeout=5000)
                page.click(selector)
                _human_delay(100, 300)
                page.fill(selector, str(value))
                _human_delay(200, 600)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not fill %s: %s", selector, exc)

        shot_before = _save_screenshot(page, "form_before_submit")

        # Submit
        try:
            page.click(submit_selector, timeout=5000)
            _human_delay(1000, 2000)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Submit click failed: %s", exc)

        shot_after = _save_screenshot(page, "form_after_submit")
        text = page.inner_text("body") or ""
        context.close()

        return BrowserResult(
            ok=True, url=url, page_text=text[:4000],
            screenshot_path=shot_after, form_submitted=True,
            timing_ms=int((time.time() - start) * 1000)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("fill_and_submit_form failed: %s", exc)
        return BrowserResult(ok=False, url=url, error=str(exc),
                             timing_ms=int((time.time() - start) * 1000))
    finally:
        if playwright:
            try:
                playwright.stop()
            except Exception:  # noqa: BLE001
                pass


def answer_and_submit_quiz(
    url: str,
    ai_answerer: Callable[[str, list], list],
    profile: Optional[str] = None,
) -> BrowserResult:
    """
    Navigate to quiz URL, extract questions, call ai_answerer to get answers,
    fill answers, submit, and take screenshot evidence.

    ai_answerer signature: (page_text: str, questions: list[dict]) -> list[dict]
    Each question dict: {index, text, type, options}
    Each answer dict:   {index, selector, value}
    """
    start = time.time()
    playwright = None
    try:
        playwright, context = _get_playwright_context(profile)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=_SCREENSHOT_TIMEOUT)
        _human_delay(1000, 2000)

        page_text = page.inner_text("body") or ""
        shot_before = _save_screenshot(page, "quiz_before")

        # Extract questions from DOM
        questions = _extract_quiz_questions(page)
        logger.info("Extracted %d questions from quiz", len(questions))

        # Get AI answers
        answers = ai_answerer(page_text, questions)
        logger.info("AI returned %d answers", len(answers))

        # Fill answers
        answered = []
        for answer in answers:
            try:
                sel = answer.get("selector", "")
                val = answer.get("value", "")
                q_type = answer.get("type", "text")

                if q_type == "radio" or q_type == "checkbox":
                    # Click the option
                    page.click(sel, timeout=5000)
                elif q_type == "select":
                    page.select_option(sel, val, timeout=5000)
                else:
                    # text / textarea
                    page.fill(sel, str(val), timeout=5000)

                _human_delay(300, 700)
                answered.append(answer)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not answer question %s: %s", answer.get("index"), exc)

        shot_filled = _save_screenshot(page, "quiz_filled")

        # Submit
        try:
            submit_sel = (
                "input[type=submit], button[type=submit], "
                "button:text('Submit'), button:text('Next'), "
                "[data-automation-id='next-button']"
            )
            page.click(submit_sel, timeout=8000)
            _human_delay(2000, 3000)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Quiz submit click failed: %s", exc)

        shot_after = _save_screenshot(page, "quiz_submitted")
        final_text = page.inner_text("body") or ""
        context.close()

        return BrowserResult(
            ok=True, url=url, page_text=final_text[:4000],
            screenshot_path=shot_after, form_submitted=True,
            quiz_answers=answered,
            timing_ms=int((time.time() - start) * 1000)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("answer_and_submit_quiz failed: %s", exc)
        return BrowserResult(ok=False, url=url, error=str(exc),
                             timing_ms=int((time.time() - start) * 1000))
    finally:
        if playwright:
            try:
                playwright.stop()
            except Exception:  # noqa: BLE001
                pass


def take_screenshot(url: str, profile: Optional[str] = None) -> BrowserResult:
    """Navigate to URL and take screenshot only."""
    start = time.time()
    playwright = None
    try:
        playwright, context = _get_playwright_context(profile)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=_SCREENSHOT_TIMEOUT)
        _human_delay(1000, 2000)
        shot = _save_screenshot(page, "screenshot")
        context.close()
        return BrowserResult(ok=True, url=url, screenshot_path=shot,
                             timing_ms=int((time.time() - start) * 1000))
    except Exception as exc:  # noqa: BLE001
        logger.exception("take_screenshot failed: %s", exc)
        return BrowserResult(ok=False, url=url, error=str(exc),
                             timing_ms=int((time.time() - start) * 1000))
    finally:
        if playwright:
            try:
                playwright.stop()
            except Exception:  # noqa: BLE001
                pass


def _extract_quiz_questions(page) -> list:
    """
    Extract quiz questions from the DOM.
    Handles Google Forms, Canvas LMS, Blackboard, Moodle, generic forms.
    Returns list of dicts: {index, text, type, options, selector}
    """
    questions = []
    try:
        # --- Google Forms ---
        gforms = page.query_selector_all("[data-params]")
        if gforms:
            for i, q_el in enumerate(gforms):
                q_text = ""
                try:
                    heading = q_el.query_selector("[role=heading]")
                    q_text = heading.inner_text() if heading else ""
                except Exception:  # noqa: BLE001
                    pass

                # Radio buttons (multiple choice)
                radios = q_el.query_selector_all("div[role=radio]")
                if radios:
                    options = []
                    for r in radios:
                        try:
                            options.append(r.inner_text().strip())
                        except Exception:  # noqa: BLE001
                            pass
                    questions.append({
                        "index": i,
                        "text": q_text,
                        "type": "radio",
                        "options": options,
                        "selector_base": f"[data-params]:nth-child({i+1}) div[role=radio]",
                    })
                    continue

                # Text input
                text_input = q_el.query_selector("input[type=text], textarea")
                if text_input:
                    questions.append({
                        "index": i,
                        "text": q_text,
                        "type": "text",
                        "options": [],
                        "selector_base": f"[data-params]:nth-child({i+1}) input[type=text], [data-params]:nth-child({i+1}) textarea",
                    })
            if questions:
                return questions

        # --- Generic fallback: find all input/select/textarea with labels ---
        inputs = page.query_selector_all("input:not([type=hidden]):not([type=submit]), select, textarea")
        for i, el in enumerate(inputs):
            try:
                el_id = el.get_attribute("id") or ""
                label = ""
                if el_id:
                    label_el = page.query_selector(f"label[for='{el_id}']")
                    label = label_el.inner_text() if label_el else ""
                input_type = el.get_attribute("type") or el.evaluate("el => el.tagName.toLowerCase()")
                tag = el.evaluate("el => el.tagName.toLowerCase()")
                q_type = "select" if tag == "select" else input_type

                questions.append({
                    "index": i,
                    "text": label or f"Field {i+1}",
                    "type": q_type,
                    "options": [],
                    "selector_base": f"#{el_id}" if el_id else f"input:nth-of-type({i+1})",
                })
            except Exception:  # noqa: BLE001
                pass

    except Exception as exc:  # noqa: BLE001
        logger.warning("_extract_quiz_questions failed: %s", exc)

    return questions
