"""
academic_agent.py — Quiz & Assignment AI Solver
=================================================
Combines playwright_agent (browser hands) with chat_service (AI brain)
to autonomously answer and submit academic quizzes.

Public interface (never raises):
  solve_quiz(url, profile, model)    -> QuizResult
  solve_assignment(url, profile)     -> QuizResult
  build_answer_prompt(page_text, questions) -> str
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jules_bridge.academic_agent")

_ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
_MEMORY_PATH = _ROOT_DIR / "memory" / "academic.md"


@dataclass
class QuizResult:
    ok: bool
    url: str = ""
    questions_found: int = 0
    questions_answered: int = 0
    screenshot_path: str = ""
    submitted: bool = False
    ai_answers: list = field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_academic_memory() -> str:
    """Load past quiz learnings from memory/academic.md."""
    try:
        if _MEMORY_PATH.exists():
            return _MEMORY_PATH.read_text(encoding="utf-8")[:3000]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load academic memory: %s", exc)
    return ""


def build_answer_prompt(page_text: str, questions: list) -> str:
    """
    Build a prompt for the AI to answer quiz questions.
    Returns a JSON-friendly prompt string.
    """
    memory = _load_academic_memory()

    questions_str = ""
    for q in questions:
        questions_str += f"\nQ{q.get('index', '?')}: {q.get('text', '')}"
        if q.get("type") == "radio" and q.get("options"):
            for j, opt in enumerate(q["options"]):
                questions_str += f"\n  [{j}] {opt}"
        questions_str += "\n"

    prompt = f"""You are an expert academic assistant helping answer quiz questions accurately.

Past memory/context (use if relevant):
{memory if memory else "(none)"}

Current quiz page context:
{page_text[:2000]}

Questions to answer:
{questions_str}

For EACH question, respond in JSON array format:
[
  {{
    "index": 0,
    "type": "radio",
    "answer_text": "The correct answer text",
    "option_index": 2,
    "confidence": 0.9
  }},
  ...
]

Rules:
- Be accurate and concise
- For multiple choice: pick the best option and include option_index
- For text/essay: write a complete, correct answer
- Set confidence 0.0-1.0 honestly
- Return ONLY the JSON array, no other text
"""
    return prompt


def _call_ai(prompt: str, model: str = "fast") -> list:
    """
    Call AI via the bridge's own /reasoning/solve route (keyless — uses whatever
    reasoning model the bridge has configured).

    Priority chain:
      1. POST http://127.0.0.1:5000/reasoning/solve  (bridge calls itself — zero keys needed)
      2. Stub answers from the prompt text itself (offline fallback)
    """
    import re  # noqa: PLC0415
    import os  # noqa: PLC0415

    bridge_url = os.environ.get("BRIDGE_URL", "http://127.0.0.1:5000")
    bridge_token = os.environ.get("BRIDGE_TOKEN", "")

    # --- Strategy 1: call bridge /reasoning/solve ---
    try:
        import urllib.request  # noqa: PLC0415
        import urllib.error  # noqa: PLC0415

        body = json.dumps({
            "problem": prompt,
            "model": model,  # "stub" works offline, "fast"/"smart" use VM loop if available
            "halt_budget": 3,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{bridge_url}/reasoning/solve",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {bridge_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        answer = data.get("answer") or data.get("trace", {}).get("answer", "")
        if answer:
            logger.info("Bridge /reasoning/solve answered (%d chars)", len(answer))
            # Try to parse JSON array from answer
            json_match = re.search(r"\[.*?\]", answer, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            # Wrap raw text answer
            return [{"index": 0, "type": "text", "answer_text": answer.strip(), "confidence": 0.85}]

    except Exception as exc:  # noqa: BLE001
        logger.warning("Bridge /reasoning/solve call failed: %s — falling back to stub", exc)

    # --- Strategy 2: offline stub — extract option-pattern answers from prompt ---
    stub_answers = []
    questions_in_prompt = re.findall(r"Q(\d+):\s*(.+?)(?=\nQ|\Z)", prompt, re.DOTALL)
    for idx_str, q_text in questions_in_prompt:
        stub_answers.append({
            "index": int(idx_str),
            "type": "text",
            "answer_text": f"[Offline — bridge model unavailable. Manual answer needed for: {q_text.strip()[:80]}]",
            "confidence": 0.1,
        })
    logger.warning("_call_ai using stub (no live model). %d questions noted.", len(stub_answers))
    return stub_answers


def _map_answers_to_selectors(questions: list, ai_answers: list) -> list:
    """
    Map AI answer objects back to browser selectors for playwright_agent.
    Returns list of {index, selector, value, type} dicts.
    """
    answer_map = {a.get("index"): a for a in ai_answers}
    result = []

    for q in questions:
        idx = q.get("index", 0)
        ai_ans = answer_map.get(idx)
        if ai_ans is None:
            continue

        q_type = q.get("type", "text")
        selector_base = q.get("selector_base", "")

        if q_type == "radio":
            # Click the specific option
            opt_idx = ai_ans.get("option_index", 0)
            if selector_base and "nth-child" in selector_base:
                # Google Forms pattern
                sel = f"{selector_base}:nth-child({opt_idx + 1})"
            else:
                sel = f"{selector_base}:nth-child({opt_idx + 1})"
            result.append({
                "index": idx,
                "selector": sel,
                "value": ai_ans.get("answer_text", ""),
                "type": "radio",
            })
        elif q_type == "select":
            result.append({
                "index": idx,
                "selector": selector_base,
                "value": ai_ans.get("answer_text", ""),
                "type": "select",
            })
        else:
            result.append({
                "index": idx,
                "selector": selector_base,
                "value": ai_ans.get("answer_text", ""),
                "type": "text",
            })

    return result


def _write_academic_memory(url: str, questions: list, ai_answers: list) -> None:
    """Append quiz Q&A to academic memory for future learning."""
    try:
        _MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = f"""
## Quiz Session — {_now_iso()}
- URL: {url}
- Questions: {len(questions)}
- Answered: {len(ai_answers)}

"""
        for q in questions:
            idx = q.get("index", "?")
            ai_ans = next((a for a in ai_answers if a.get("index") == idx), None)
            entry += f"**Q{idx}**: {q.get('text', '')}\n"
            if ai_ans:
                entry += f"**A**: {ai_ans.get('answer_text', '')} (confidence: {ai_ans.get('confidence', '?')})\n"
            entry += "\n"

        if _MEMORY_PATH.exists():
            existing = _MEMORY_PATH.read_text(encoding="utf-8")
        else:
            existing = "# Academic Memory\n\nLearnings from past quizzes and assignments.\n"

        _MEMORY_PATH.write_text(existing + entry, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("_write_academic_memory failed: %s", exc)


def solve_quiz(
    url: str,
    profile: Optional[str] = None,
    model: str = "fast",
) -> QuizResult:
    """
    Full autonomous quiz solver:
    1. Navigate to quiz URL (using authenticated Chrome session)
    2. Extract all questions from DOM
    3. Build AI prompt → call chat_service
    4. Map answers → fill + submit via playwright
    5. Screenshot evidence + write to academic memory
    """
    from modules.playwright_agent import answer_and_submit_quiz  # lazy import

    try:
        # Build the answerer callback for playwright_agent
        def ai_answerer(page_text: str, questions: list) -> list:
            prompt = build_answer_prompt(page_text, questions)
            ai_answers = _call_ai(prompt, model=model)
            logger.info("AI answered %d questions", len(ai_answers))
            mapped = _map_answers_to_selectors(questions, ai_answers)
            # Store AI answers for result reporting
            ai_answerer._last_answers = ai_answers  # type: ignore[attr-defined]
            ai_answerer._last_questions = questions  # type: ignore[attr-defined]
            return mapped

        ai_answerer._last_answers = []  # type: ignore[attr-defined]
        ai_answerer._last_questions = []  # type: ignore[attr-defined]

        browser_result = answer_and_submit_quiz(url, ai_answerer, profile=profile)

        # Write to memory regardless of outcome
        _write_academic_memory(
            url,
            getattr(ai_answerer, "_last_questions", []),
            getattr(ai_answerer, "_last_answers", []),
        )

        return QuizResult(
            ok=browser_result.ok,
            url=url,
            questions_found=len(getattr(ai_answerer, "_last_questions", [])),
            questions_answered=len(browser_result.quiz_answers),
            screenshot_path=browser_result.screenshot_path,
            submitted=browser_result.form_submitted,
            ai_answers=getattr(ai_answerer, "_last_answers", []),
            error=browser_result.error,
            timestamp=_now_iso(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("solve_quiz failed: %s", exc)
        return QuizResult(ok=False, url=url, error=str(exc), timestamp=_now_iso())


def solve_assignment(url: str, profile: Optional[str] = None) -> QuizResult:
    """
    Read assignment page, generate an answer/essay with AI, return the text.
    (Filling depends on the specific platform — caller handles submission.)
    """
    from modules.playwright_agent import read_page_text  # lazy import

    try:
        browser_result = read_page_text(url, profile)
        if not browser_result.ok:
            return QuizResult(ok=False, url=url, error=browser_result.error, timestamp=_now_iso())

        prompt = f"""You are helping complete an academic assignment. 
Read the following assignment description and write a complete, high-quality response.

Assignment page content:
{browser_result.page_text[:4000]}

Write a thorough, academically appropriate response. Be specific and detailed.
"""
        ai_answers = _call_ai(prompt, model="smart")
        return QuizResult(
            ok=True, url=url,
            questions_found=1, questions_answered=1,
            screenshot_path=browser_result.screenshot_path,
            ai_answers=ai_answers,
            timestamp=_now_iso(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("solve_assignment failed: %s", exc)
        return QuizResult(ok=False, url=url, error=str(exc), timestamp=_now_iso())
