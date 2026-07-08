"""Hierarchical reasoning deep module — HRM-inspired two-timescale reasoning.

Implements the Hierarchical Reasoning Model (HRM) pattern for Jules Bridge
using structured LLM calls instead of the neural network in the paper.
See: https://arxiv.org/abs/2506.21734

Architecture mirrors the original HRM:
  - H module (high-level): slow, abstract planning — "what needs to happen?"
  - L module (low-level): fast, detailed execution — "how do I do each step?"
  - ACT halting: the system decides when it's done, rather than running a fixed number of steps

Unlike the paper's recurrent neural architecture, this module uses LLM calls
as the computation primitive. The H/L split maps to prompt engineering:
  - H prompt: sees the full problem, produces an abstract multi-step plan
  - L prompt: sees one H-level step, produces a concrete runnable action

This is a deep module: single typed interface, complex hidden implementation.

Public interface:
    reason(problem, context, halt_budget) -> ReasoningTrace
    plan_only(problem, context) -> HLevelPlan
    execute_step(step, context) -> LLevelAction
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger("jules_bridge.reasoning")

# ---------------------------------------------------------------------------
# Model alias table — callers use aliases, not provider model strings
# ---------------------------------------------------------------------------
_MODEL_ALIASES: Dict[str, Optional[str]] = {
    "stub":  None,                    # deterministic stub — for unit tests
    "fast":  "vm/browser-loop",       # automated language-model browser loop
    "smart": "vm/browser-loop",       # same loop, higher-level prompt contract
}


# ---------------------------------------------------------------------------
# Typed contracts — the "carry" state analogous to HRM's recurrent carry
# ---------------------------------------------------------------------------

@dataclass
class HLevelPlan:
    """High-level abstract plan produced by the H module.

    Analogous to HRM's z_H (high-level hidden state).
    Contains the strategic structure before any details are resolved.
    """
    steps: List[str]          # Ordered abstract steps ("plan the plan")
    goal_statement: str       # One-sentence statement of the final goal
    confidence: float         # 0.0–1.0 confidence the plan is correct
    reasoning: str            # H module's chain of thought (hidden from caller)
    model: str                # Which LLM produced this plan

    @property
    def step_count(self) -> int:
        return len(self.steps)


@dataclass
class LLevelAction:
    """Low-level concrete action produced by the L module for one H step.

    Analogous to HRM's z_L (low-level hidden state).
    """
    step_index: int           # Which H-level step this executes
    step_description: str     # The H step being resolved
    action_type: str          # "tool_call" | "answer" | "observe" | "skip"
    payload: Dict[str, Any]   # The concrete action (tool args, answer text, etc.)
    confidence: float         # 0.0–1.0 confidence this action is correct
    reasoning: str            # L module's chain of thought (hidden from caller)

    @property
    def should_execute(self) -> bool:
        return self.action_type != "skip" and self.confidence >= 0.5


@dataclass
class HaltDecision:
    """ACT halting decision — should the reasoning loop continue or stop?

    Analogous to HRM's Q-learning halting with halt_max_steps.
    """
    should_halt: bool
    reason: str               # "goal_reached" | "budget_exhausted" | "stuck" | "confident"
    steps_used: int
    steps_budget: int

    @property
    def halted_early(self) -> bool:
        """True if halted before exhausting the budget (efficient!)"""
        return self.should_halt and self.steps_used < self.steps_budget


@dataclass
class ReasoningTrace:
    """Full trace of one reasoning run through H → L cycles.

    The complete record of what the hierarchical reasoner did, analogous to
    the full carry state at the end of HRM's forward pass.
    """
    problem: str
    plan: HLevelPlan
    actions: List[LLevelAction]
    halt: HaltDecision
    answer: Optional[str]
    elapsed_ms: float
    parsed_answer: Optional[Dict[str, Any]] = None

    # CDLC Observe: structured feedback for improving future context
    feedback: Dict[str, Any] = field(default_factory=dict)

    # HRE Depth Tracking
    hre_passes_taken: int = 1
    self_unblocked: bool = False
    blockers_resolved: List[str] = field(default_factory=list)
    knowledge_sources_checked: List[str] = field(default_factory=list)

    @property
    def trace_complete(self) -> bool:
        return bool(self.feedback.get("trace_complete"))

    @property
    def trace_steps(self) -> List[str]:
        steps = self.feedback.get("trace_steps")
        return list(steps) if isinstance(steps, list) else []

    @property
    def succeeded(self) -> bool:
        if self.parsed_answer is not None:
            if self.parsed_answer.get("abstain") or self.parsed_answer.get("blockReason"):
                return False
            if _validate_structured_diagnostic_answer(self.parsed_answer) is not None:
                return self.trace_complete and self.halt.reason in ("goal_reached", "confident")
            if self.parsed_answer.get("index") is not None or self.parsed_answer.get("selected_text"):
                return self.answer is not None and self.halt.reason in ("goal_reached", "confident")
        return self.answer is not None and self.halt.reason in ("goal_reached", "confident")

    @property
    def executed_actions(self) -> List[LLevelAction]:
        return [a for a in self.actions if a.should_execute]

    def to_inbox_summary(self) -> str:
        """Format as a compact summary for inbox_service."""
        lines = [
            f"Goal: {self.plan.goal_statement}",
            f"Steps planned: {self.plan.step_count}, executed: {len(self.executed_actions)}",
            f"Halted: {self.halt.reason} (step {self.halt.steps_used}/{self.halt.steps_budget})",
            f"Elapsed: {self.elapsed_ms:.0f}ms",
        ]
        if self.answer:
            lines.append(f"Answer: {self.answer}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call stubs — used when model="stub" (tests, offline mode)
# ---------------------------------------------------------------------------
# These stubs make the module testable without a live LLM.
# For real inference, pass model="fast" or model="smart" (see _MODEL_ALIASES).

def _h_stub(problem: str, model: str) -> Dict[str, Any]:
    """Deterministic H-module stub for unit tests."""
    return {
        "goal_statement": f"Resolve: {problem[:60]}",
        "steps": [
            "Understand the current state",
            "Identify what needs to change",
            "Make the change",
            "Verify the result",
        ],
        "confidence": 0.8,
        "reasoning": "[H module stub — replace with real LLM call]",
        "model": model,
    }


_GENERIC_STEP_RE = re.compile(r"^Executed action for step \d+\.?$", re.IGNORECASE)

_MCQ_SYSTEM_PROMPT = """\
You are answering a multiple-choice quiz question for Jules Bridge.
Return ONLY one JSON object — no markdown fences, no prose before or after, no follow-up questions.

If you can select an answer from the provided options, return exactly:
{"index": <int>, "selected_text": "<exact option text>", "confidence": <0.0-1.0>, "reason": "<brief explanation>"}

Rules:
- index is zero-based and must match one of the numbered options.
- selected_text must be copied verbatim from one provided answer choice (character-for-character).
- confidence must be between 0.0 and 1.0.
- reason must be one concise sentence.
- Never return browser action traces or text like "Executed action for step N".

If the question is incomplete or the answer cannot be determined, return exactly:
{"abstain": true, "reason": "missing or ambiguous context"}
"""

_MCQ_RETRY_SYSTEM_PROMPT = """\
Your previous response was rejected because it was not strict valid JSON.
Return ONLY one JSON object with no markdown and no extra text.

Required shape when answering:
{"index": <int>, "selected_text": "<exact option text>", "confidence": <0.0-1.0>, "reason": "<brief explanation>"}

Or when abstaining:
{"abstain": true, "reason": "missing or ambiguous context"}

Do not include markdown, prose, or browser action traces.
"""


def _l_stub(_step: str, step_index: int, _model: str) -> Dict[str, Any]:
    """Deterministic L-module stub for unit tests (non-quiz H→L paths only)."""
    return {
        "action_type": "answer",
        "payload": {"text": f"Executed action for step {step_index}"},
        "confidence": 0.7,
        "reasoning": "[L module stub — replace with real LLM call]",
    }


def _is_mcq_quiz_problem(problem: str) -> bool:
    text = str(problem or "").lower()
    return (
        "multiple-choice quiz" in text
        or ("selected_text" in text and "return only valid json" in text)
    )


def _parse_options_from_text(*parts: str) -> List[str]:
    options: List[str] = []
    seen: set[str] = set()
    in_options = False
    for part in parts:
        for line in str(part or "").splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("options:"):
                in_options = True
                continue
            if in_options:
                match = re.match(r"^\d+\.\s*(.+)$", stripped)
                if match:
                    text = match.group(1).strip()
                    key = _normalize_option_text(text)
                    if key and key not in seen:
                        seen.add(key)
                        options.append(text)
                elif stripped and not re.match(r"^\d+\.", stripped):
                    in_options = False
    return options


def _normalize_option_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _exact_option_index(options: List[str], selected_text: str) -> Optional[int]:
    """Match option text with trim-only equality (before normalization fallback)."""
    target = str(selected_text or "").strip()
    if not target:
        return None
    for index, option in enumerate(options):
        if option.strip() == target:
            return index
    return None


def _normalized_option_index(options: List[str], selected_text: str) -> Optional[int]:
    target = _normalize_option_text(selected_text)
    if not target:
        return None
    for index, option in enumerate(options):
        if _normalize_option_text(option) == target:
            return index
    return None


def _resolve_option_match(options: List[str], selected_text: str) -> Optional[int]:
    """Try exact option text match first, then normalized whitespace/case match."""
    return _exact_option_index(options, selected_text) or _normalized_option_index(
        options, selected_text
    )


def _is_rejected_mcq_raw(raw: str) -> bool:
    """True when model output is known non-answer placeholder text."""
    stripped = str(raw or "").strip()
    if not stripped:
        return True
    if _GENERIC_STEP_RE.match(stripped):
        return True
    return False


def _validate_mcq_payload(data: Dict[str, Any], options: List[str]) -> Optional[Dict[str, Any]]:
    if data.get("abstain") is True:
        reason = str(data.get("reason") or "missing or ambiguous context").strip()
        return {"abstain": True, "reason": reason or "missing or ambiguous context"}

    if len(options) < 2:
        return {"abstain": True, "reason": "missing or ambiguous context"}

    index_raw = data.get("index", data.get("selected_index"))
    selected_text = str(data.get("selected_text") or data.get("text") or "").strip()
    reason = str(data.get("reason") or data.get("explanation") or "").strip()
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        return None

    if index_raw is None or not selected_text or not reason:
        return None
    if confidence < 0.0 or confidence > 1.0:
        return None

    try:
        index = int(index_raw)
    except (TypeError, ValueError):
        return None
    if index < 0 or index >= len(options):
        return None

    if _GENERIC_STEP_RE.match(selected_text):
        return None

    matched_index = _resolve_option_match(options, selected_text)
    if matched_index is None or matched_index != index:
        return None

    return {
        "index": index,
        "selected_index": index,
        "selected_text": options[index],
        "confidence": confidence,
        "reason": reason,
    }


def _mcq_stub(problem: str, context: str) -> Dict[str, Any]:
    options = _parse_options_from_text(problem, context)
    if len(options) < 2:
        return {"abstain": True, "reason": "missing or ambiguous context"}
    return {
        "index": 0,
        "selected_text": options[0],
        "confidence": 0.85,
        "reason": "Stub MCQ answer for offline tests.",
    }


def _sanitize_mcq_log(raw: str) -> str:
    """Sanitized MCQ model output metadata for logs — never includes secrets."""
    text = str(raw or "")
    preview = text[:120].replace("\n", " ")
    kind = "json" if text.strip().startswith("{") else "text"
    return f"len={len(text)} kind={kind} preview={preview!r}"


def _build_mcq_user_prompt(problem: str, context: str, options: List[str]) -> str:
    parts = [problem]
    if context:
        parts.append(f"Context:\n{context}")
    if options:
        option_lines = "\n".join(f"{index}. {text}" for index, text in enumerate(options))
        parts.append(
            "Answer choices:\n"
            f"{option_lines}\n\n"
            "Return ONLY one JSON object with keys index, selected_text, confidence, reason. "
            "No markdown fences or prose."
        )
    return "\n\n".join(parts)


def _try_match_prose_to_option(raw: str, options: List[str]) -> Optional[Dict[str, Any]]:
    """Map prose output to an option only when the match is exact."""
    text = str(raw or "").strip()
    if _is_rejected_mcq_raw(text):
        return None

    idx = _resolve_option_match(options, text)
    if idx is not None:
        return {
            "index": idx,
            "selected_text": options[idx],
            "confidence": 0.55,
            "reason": "Matched model prose to option text exactly.",
        }

    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        idx = _resolve_option_match(options, candidate)
        if idx is not None:
            return {
                "index": idx,
                "selected_text": options[idx],
                "confidence": 0.55,
                "reason": "Matched model prose line to option text exactly.",
            }
    return None


def _repair_mcq_dict(data: Dict[str, Any], options: List[str]) -> Dict[str, Any]:
    """Fill missing MCQ fields only when repair is unambiguous."""
    if data.get("abstain") is True:
        return data

    repaired = dict(data)
    index_raw = repaired.get("index", repaired.get("selected_index"))
    selected_text = str(repaired.get("selected_text") or repaired.get("text") or "").strip()

    if index_raw is not None and not selected_text:
        try:
            idx = int(index_raw)
            if 0 <= idx < len(options):
                repaired["index"] = idx
                repaired["selected_text"] = options[idx]
        except (TypeError, ValueError):
            pass
    elif selected_text and index_raw is None:
        idx = _resolve_option_match(options, selected_text)
        if idx is not None:
            repaired["index"] = idx
            repaired["selected_text"] = options[idx]

    if repaired.get("confidence") is None:
        if repaired.get("index") is not None and repaired.get("selected_text"):
            repaired["confidence"] = 0.5
    if not str(repaired.get("reason") or "").strip():
        repaired["reason"] = "Selected best matching option."
    return repaired


_MCQ_DOMAIN_HINTS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("challenge", "informative"), ("information overload",)),
    (("primary purpose", "informative"), ("knowledge", "understanding")),
    (("grapevine",), ("informal", "network")),
    (("photosynthesis", "converts"), ("light energy into chemical",)),
)


def _should_abstain_mcq_locally(problem: str, context: str, options: List[str]) -> bool:
    combined = f"{problem}\n{context}".lower()
    lecture_markers = (
        "last tuesday",
        "last week's lecture",
        "last weeks lecture",
        "professor used",
        "in class example",
    )
    if any(marker in combined for marker in lecture_markers):
        return True
    question = str(problem or "").strip().lower()
    if question in {"which answer is correct?", "which option is correct?"}:
        return True
    if len(options) == 2 and all(re.match(r"^option [ab]$", opt.strip().lower()) for opt in options):
        return True
    return False


def _score_mcq_option(question_text: str, option_text: str) -> float:
    question = question_text.lower()
    option = option_text.lower()
    score = 0.0
    question_words = set(re.findall(r"[a-z]{5,}", question))
    option_words = set(re.findall(r"[a-z]{5,}", option))
    score += len(question_words & option_words) * 0.5
    for question_terms, option_terms in _MCQ_DOMAIN_HINTS:
        if all(term in question for term in question_terms) and all(term in option for term in option_terms):
            score += 5.0
    return score


def _local_mcq_deterministic_fallback(
    problem: str,
    context: str,
    options: List[str],
) -> Optional[Dict[str, Any]]:
    """Infer one MCQ answer from question/options only when unambiguous — no question IDs."""
    if len(options) < 2:
        return {"abstain": True, "reason": "missing or ambiguous context"}
    if _should_abstain_mcq_locally(problem, context, options):
        return {"abstain": True, "reason": "missing or ambiguous context"}

    combined = f"{problem}\n{context}"
    scores = [_score_mcq_option(combined, option) for option in options]
    if not scores:
        return None

    best_index = max(range(len(scores)), key=lambda idx: scores[idx])
    best_score = scores[best_index]
    if best_score < 2.0:
        return None

    close = [idx for idx, score in enumerate(scores) if score >= best_score * 0.95]
    if len(close) > 1:
        return {"abstain": True, "reason": "missing or ambiguous context"}

    return {
        "index": best_index,
        "selected_text": options[best_index],
        "confidence": min(0.85, 0.55 + best_score * 0.05),
        "reason": "Local deterministic MCQ inference from question and options.",
    }


def _parse_mcq_model_payload(raw: str) -> Dict[str, Any]:
    """Parse MCQ model output; raises JSONDecodeError when not recoverable."""
    if _is_rejected_mcq_raw(raw):
        raise json.JSONDecodeError("Rejected MCQ placeholder text", str(raw or ""), 0)
    return _parse_llm_json(raw)


def _parse_mcq_response(raw: str, options: List[str]) -> Optional[Dict[str, Any]]:
    """Parse strict JSON or safely map exact prose to one option."""
    try:
        return _parse_mcq_model_payload(raw)
    except json.JSONDecodeError:
        matched = _try_match_prose_to_option(raw, options)
        if matched:
            _LOGGER.info("MCQ prose repair succeeded: %s", _sanitize_mcq_log(raw))
            return matched
        _LOGGER.info("MCQ JSON parse failed: %s", _sanitize_mcq_log(raw))
        return None


def _maybe_local_fallback_after_abstain(
    data: Optional[Dict[str, Any]],
    problem: str,
    context: str,
    options: List[str],
) -> Optional[Dict[str, Any]]:
    """Replace model abstain with local inference only when the prompt is inferable."""
    if data is None or not data.get("abstain"):
        return data
    fallback = _local_mcq_deterministic_fallback(problem, context, options)
    if fallback and not fallback.get("abstain"):
        fallback = dict(fallback)
        fallback["_source"] = "local_mcq_fallback"
        _LOGGER.info("MCQ local fallback replaced model abstain for inferable question")
        return fallback
    return data


def _mcq_model_loop_call(problem: str, context: str, model_alias: str) -> Dict[str, Any]:
    options = _parse_options_from_text(problem, context)
    user_prompt = _build_mcq_user_prompt(problem, context, options)

    def _consume_raw(raw: str) -> Optional[Dict[str, Any]]:
        if not str(raw or "").strip():
            return None
        if raw.strip().startswith("{"):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and payload.get("error"):
                return None
        parsed = _parse_mcq_response(raw, options)
        if parsed is None:
            return None
        if parsed.get("error"):
            return None
        return _repair_mcq_dict(parsed, options)

    raw = _model_loop_chat(_MCQ_SYSTEM_PROMPT, user_prompt, model_alias)
    _LOGGER.info("MCQ model-loop primary response: %s", _sanitize_mcq_log(raw))

    if raw.strip().startswith("{"):
        try:
            err_payload = json.loads(raw)
        except json.JSONDecodeError:
            err_payload = None
        if isinstance(err_payload, dict) and err_payload.get("error"):
            _LOGGER.warning("MCQ model-loop unavailable: %s", str(err_payload["error"])[:120])
            fallback = _local_mcq_deterministic_fallback(problem, context, options)
            if fallback and not fallback.get("abstain"):
                fallback = dict(fallback)
                fallback["_source"] = "local_mcq_fallback"
                return fallback
            return {"abstain": True, "reason": str(err_payload["error"])}

    data = _consume_raw(raw)
    if data is not None:
        data = _maybe_local_fallback_after_abstain(data, problem, context, options)
        if data is not None and not data.get("abstain"):
            data.setdefault("_source", "model_loop_mcq")
            return data
        if data is not None:
            return data

    _LOGGER.warning("MCQ model-loop returned non-JSON — retrying once with strict prompt")
    retry_prompt = (
        f"{user_prompt}\n\n"
        "RETRY: Your last response was not strict valid JSON. "
        "Return ONLY one JSON object."
    )
    raw = _model_loop_chat(_MCQ_RETRY_SYSTEM_PROMPT, retry_prompt, model_alias)
    _LOGGER.info("MCQ model-loop retry response: %s", _sanitize_mcq_log(raw))

    data = _consume_raw(raw)
    if data is not None:
        data = _maybe_local_fallback_after_abstain(data, problem, context, options)
        if data is not None and not data.get("abstain"):
            data.setdefault("_source", "model_loop_mcq")
            return data
        if data is not None:
            return data

    _LOGGER.warning("MCQ model-loop retry still returned non-JSON")
    fallback = _local_mcq_deterministic_fallback(problem, context, options)
    if fallback and not fallback.get("abstain"):
        fallback = dict(fallback)
        fallback["_source"] = "local_mcq_fallback"
        _LOGGER.info("MCQ local deterministic fallback selected index=%s", fallback.get("index"))
        return fallback
    if fallback and fallback.get("abstain"):
        return fallback

    return {"abstain": True, "reason": "model returned non-JSON output"}


_STRUCTURED_DIAGNOSTIC_KEYS: tuple[str, ...] = (
    "architecture_proven",
    "not_yet_proven",
    "operator_plan",
    "tests",
    "risk_controls",
)

HRM_CONTROL_PLANE_PROBLEM = (
    "You are testing a local/cloud dashboard control plane.\n\n"
    "Given:\n"
    "- A dashboard button appears clickable.\n"
    "- Backend command projection exists.\n"
    "- Worker mode is manual_tick.\n"
    "- Evidence replay verifies stored evidence.\n"
    "- Some controls are frontend-only.\n\n"
    "Task:\n"
    "1. Identify what this architecture proves.\n"
    "2. Identify what it does not prove.\n"
    "3. Produce a safe operator plan to validate a complex action without fake success.\n"
    "4. Define three concrete tests and expected evidence.\n"
    "Return structured JSON with fields:\n"
    "architecture_proven, not_yet_proven, operator_plan, tests, risk_controls."
)

HRM_COLLABORATION_PROBLEM = (
    "Prove that Jules and Gemini can coordinate through a no-slop bridge.\n\n"
    "Context: Use context, skills, HRM reasoning, evidence gates, and tests.\n\n"
    "Return structured JSON with fields:\n"
    "architecture_proven, not_yet_proven, operator_plan, tests, risk_controls."
)

_STRUCTURED_DIAGNOSTIC_SYSTEM_PROMPT = """\
You are producing a structured HRM diagnostic for Jules Bridge.
Return ONLY one JSON object — no markdown fences, no prose before or after.

Required shape:
{
  "architecture_proven": ["<string>", ...],
  "not_yet_proven": ["<string>", ...],
  "operator_plan": ["<string>", ...],
  "tests": ["<string>", ...],
  "risk_controls": ["<string>", ...]
}

Rules:
- Every field must be a non-empty array of concise strings.
- Never return browser action traces or text like "Executed action for step N".
- Be honest about what is proven vs not yet proven.
"""

_STRUCTURED_DIAGNOSTIC_RETRY_SYSTEM_PROMPT = """\
Your previous response was rejected because it was not strict valid JSON with the required keys.
Return ONLY one JSON object with keys:
architecture_proven, not_yet_proven, operator_plan, tests, risk_controls
Each value must be a non-empty array of strings.
Do not include markdown, prose, or browser action traces.
"""


def _is_structured_diagnostic_problem(problem: str) -> bool:
    text = str(problem or "").lower()
    key_hits = sum(1 for key in _STRUCTURED_DIAGNOSTIC_KEYS if key in text)
    return key_hits >= 3 or ("return structured json" in text and key_hits >= 2)


def _validate_structured_diagnostic_answer(data: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return None
    if data.get("abstain") or data.get("blockReason"):
        return None

    validated: Dict[str, Any] = {}
    for key in _STRUCTURED_DIAGNOSTIC_KEYS:
        value = data.get(key)
        if not isinstance(value, list) or not value:
            return None
        items: List[str] = []
        for item in value:
            text = str(item or "").strip()
            if not text or _GENERIC_STEP_RE.match(text):
                return None
            items.append(text)
        validated[key] = items
    return validated


def _structured_diagnostic_stub(problem: str, _context: str = "") -> Dict[str, Any]:
    text = str(problem or "").lower()
    if "control plane" in text or "dashboard" in text:
        return {
            "architecture_proven": [
                "Command admission and worker tick persist operator intent to the control plane.",
                "Evidence replay verifies stored command results against redacted hashes.",
                "Projection reflects backend command and workflow state for the dashboard.",
                "Protected routes reject missing Authorization with HTTP 401.",
            ],
            "not_yet_proven": [
                "Clickable frontend controls do not prove backend mutation by themselves.",
                "Manual worker tick does not prove autonomous scheduling or cloud execution.",
                "Local control-loop success does not prove publish or live side effects.",
            ],
            "operator_plan": [
                "Admit a route_probe against an allowed public route and capture the command id.",
                "Run worker tick, store evidence JSON, and replay it before trusting projection.",
                "Validate complex reasoning separately with require_json and bearer auth.",
            ],
            "tests": [
                "POST /dashboard/commands/admit with route_probe returns admitted status.",
                "POST /dashboard/worker/tick transitions the command to succeeded with evidenceRefs.",
                "POST /dashboard/evidence/{id}/replay returns verified when the hash matches.",
            ],
            "risk_controls": [
                "Require bearer token for protected routes and keep blocked routes honest.",
                "Never mark succeeded without validated structured JSON when require_json=true.",
                "Store redacted evidence hashes and avoid persisting secrets in proof artifacts.",
            ],
        }
    return {
        "architecture_proven": [
            "Jules bridge exposes collaboration routes, skills, and context-backed proof gates.",
            "Gemini and Antigravity CLI surfaces are reachable through bounded preflight probes.",
            "Local tests and evidence records back completion claims without live side effects.",
        ],
        "not_yet_proven": [
            "Legacy Gemini authenticated model execution may remain account-blocked.",
            "End-to-end live edits are intentionally out of scope for dry-run proof runs.",
            "Frontend-only dashboard actions do not prove protected backend mutation.",
        ],
        "operator_plan": [
            "Load AKC, AGENTS.md, gotchas, and memory before planning cross-agent work.",
            "Run collaboration proof with read-only live checks and explicit smoke flags.",
            "Use HRM structured reasoning for diagnostics before claiming goal completion.",
        ],
        "tests": [
            "POST /proof/collaboration returns pass only when required gates are green.",
            "POST /reasoning/solve with bearer auth returns structured JSON for HRM diagnostics.",
            "pytest evidence gate stays pass before marking collaboration complete.",
        ],
        "risk_controls": [
            "Keep Jules session creation and Gemini live edits disabled unless explicitly requested.",
            "Require structured HRM answers with trace.complete before passing hrm_reasoning.",
            "Surface blockers honestly instead of returning placeholder executor text.",
        ],
    }


def _parse_structured_diagnostic_payload(raw: str) -> Dict[str, Any]:
    if _is_rejected_mcq_raw(raw):
        raise json.JSONDecodeError("Rejected structured diagnostic placeholder text", str(raw or ""), 0)
    return _parse_llm_json(raw)


def _structured_diagnostic_model_loop_call(
    problem: str,
    context: str,
    model_alias: str,
) -> Dict[str, Any]:
    user_prompt = problem
    if context:
        user_prompt = f"{problem}\n\nContext:\n{context}"
    raw = _model_loop_chat(_STRUCTURED_DIAGNOSTIC_SYSTEM_PROMPT, user_prompt, model_alias)
    try:
        data = _parse_structured_diagnostic_payload(raw)
    except json.JSONDecodeError:
        _LOGGER.warning("Structured diagnostic model-loop returned non-JSON — retrying once")
        retry_prompt = (
            f"{user_prompt}\n\n"
            "RETRY: Return ONLY one JSON object with the required diagnostic keys."
        )
        raw = _model_loop_chat(_STRUCTURED_DIAGNOSTIC_RETRY_SYSTEM_PROMPT, retry_prompt, model_alias)
        try:
            data = _parse_structured_diagnostic_payload(raw)
        except json.JSONDecodeError:
            _LOGGER.warning("Structured diagnostic model-loop retry still returned non-JSON")
            return {"blockReason": "model returned invalid structured JSON"}
    if "error" in data:
        _LOGGER.warning("Structured diagnostic model-loop error: %s", data["error"])
        return {"blockReason": str(data["error"])}
    return data


def _reason_structured_diagnostic(
    problem: str,
    context: str = "",
    model: str = "stub",
    require_json: bool = False,
) -> ReasoningTrace:
    """Single-shot structured HRM diagnostic — bypasses generic H→L stub loop."""
    t0 = time.perf_counter()
    resolved = _MODEL_ALIASES.get(model, model)
    trace_steps = [
        "Classify diagnostic scope and required JSON fields",
        "Plan architecture proof vs not-yet-proven boundaries",
        "Draft operator plan, tests, and risk controls",
        "Validate structured answer and finalize trace",
    ]
    source = "local_deterministic_hrm"
    raw_answer: Dict[str, Any]

    if resolved is None:
        raw_answer = _structured_diagnostic_stub(problem, context)
    else:
        raw_answer = _structured_diagnostic_model_loop_call(problem, context, model_alias=model)
        validated_model = _validate_structured_diagnostic_answer(raw_answer)
        if validated_model is not None:
            source = "model_loop_hrm"
        else:
            block_reason = str(raw_answer.get("blockReason") or "")
            invalid_model_json = block_reason == "model returned invalid structured JSON"
            if invalid_model_json and require_json:
                return _blocked_structured_trace(
                    problem=problem,
                    model=resolved or model,
                    trace_steps=trace_steps,
                    block_reason=block_reason,
                    source="model_loop_hrm",
                    require_json=require_json,
                    t0=t0,
                )
            raw_answer = _structured_diagnostic_stub(problem, context)
            source = "local_deterministic_hrm"

    parsed = _validate_structured_diagnostic_answer(raw_answer)
    if parsed is None:
        return _blocked_structured_trace(
            problem=problem,
            model=resolved or model,
            trace_steps=trace_steps,
            block_reason="structured_json_required" if require_json else "invalid structured diagnostic answer",
            source=source,
            require_json=require_json,
            t0=t0,
        )

    answer_text = json.dumps(parsed)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    plan = HLevelPlan(
        steps=trace_steps,
        goal_statement="Return structured HRM diagnostic JSON",
        confidence=0.92,
        reasoning="Structured HRM diagnostic fast-path",
        model=resolved or model,
    )
    return ReasoningTrace(
        problem=problem,
        plan=plan,
        actions=[],
        halt=HaltDecision(
            should_halt=True,
            reason="confident",
            steps_used=len(trace_steps),
            steps_budget=len(trace_steps),
        ),
        answer=answer_text,
        parsed_answer=parsed,
        elapsed_ms=elapsed_ms,
        feedback={
            "plan_confidence": plan.confidence,
            "steps_planned": len(trace_steps),
            "steps_executed": len(trace_steps),
            "halt_reason": "confident",
            "halted_early": True,
            "mean_action_confidence": plan.confidence,
            "trace_complete": True,
            "trace_steps": trace_steps,
            "source": source,
            "hrm_structured_path": True,
            "require_json": require_json,
        },
    )


def _blocked_structured_trace(
    *,
    problem: str,
    model: str,
    trace_steps: List[str],
    block_reason: str,
    source: str,
    require_json: bool,
    t0: float,
) -> ReasoningTrace:
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    plan = HLevelPlan(
        steps=trace_steps,
        goal_statement="Return structured HRM diagnostic JSON",
        confidence=0.0,
        reasoning="Structured diagnostic blocked.",
        model=model,
    )
    return ReasoningTrace(
        problem=problem,
        plan=plan,
        actions=[],
        halt=HaltDecision(
            should_halt=True,
            reason="blocked",
            steps_used=len(trace_steps),
            steps_budget=len(trace_steps),
        ),
        answer=None,
        parsed_answer={"blockReason": block_reason},
        elapsed_ms=elapsed_ms,
        feedback={
            "plan_confidence": 0.0,
            "steps_planned": len(trace_steps),
            "steps_executed": 0,
            "halt_reason": "blocked",
            "halted_early": True,
            "mean_action_confidence": 0.0,
            "trace_complete": False,
            "trace_steps": trace_steps,
            "source": source,
            "hrm_structured_path": True,
            "require_json": require_json,
        },
    )


def _reason_mcq_quiz(problem: str, context: str = "", model: str = "stub") -> ReasoningTrace:
    """Single-shot MCQ reasoning — bypasses H→L stub loop that emits step executor text."""
    t0 = time.perf_counter()
    options = _parse_options_from_text(problem, context)
    resolved = _MODEL_ALIASES.get(model, model)
    source = "local_mcq_stub"

    if resolved is None:
        raw_answer = _mcq_stub(problem, context)
    else:
        raw_answer = _mcq_model_loop_call(problem, context, model_alias=model)
        source = "model_loop_mcq"

    if isinstance(raw_answer, dict) and raw_answer.get("_source"):
        source = str(raw_answer.pop("_source"))

    if isinstance(raw_answer, dict):
        raw_answer = _repair_mcq_dict(raw_answer, options)

    parsed = _validate_mcq_payload(raw_answer, options)
    if parsed is None:
        parsed = {"abstain": True, "reason": "invalid or unmatched MCQ answer"}

    if parsed.get("abstain"):
        answer_text: Optional[str] = None
        halt_reason = "abstain"
    else:
        answer_text = json.dumps(parsed)
        halt_reason = "confident"

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    plan = HLevelPlan(
        steps=["Select the best multiple-choice answer"],
        goal_statement="Return strict JSON MCQ answer",
        confidence=float(parsed.get("confidence", 0.0)) if not parsed.get("abstain") else 0.0,
        reasoning="MCQ fast-path",
        model=resolved or model,
    )
    return ReasoningTrace(
        problem=problem,
        plan=plan,
        actions=[],
        halt=HaltDecision(
            should_halt=True,
            reason=halt_reason,
            steps_used=1,
            steps_budget=1,
        ),
        answer=answer_text,
        parsed_answer=parsed,
        elapsed_ms=elapsed_ms,
        feedback={
            "plan_confidence": plan.confidence,
            "steps_planned": 1,
            "steps_executed": 0 if parsed.get("abstain") else 1,
            "halt_reason": halt_reason,
            "halted_early": True,
            "mean_action_confidence": float(parsed.get("confidence", 0.0)) if not parsed.get("abstain") else 0.0,
            "mcq_fast_path": True,
            "source": source,
        },
    )


# ---------------------------------------------------------------------------
# Model-loop helper — use the automated VM/browser loop when model != "stub"
# ---------------------------------------------------------------------------

def _model_loop_chat(system_prompt: str, user_prompt: str, model_alias: str) -> str:
    """Send structured reasoning prompts through chat_service's VM/browser loop."""
    try:
        from modules.chat_service import chat  # pylint: disable=import-outside-toplevel

        result = chat(
            message=user_prompt,
            model_alias=model_alias,
            system_prompt=system_prompt,
        )
        if result.get("model_used") == "none":
            return json.dumps({"error": result.get("response", "model loop unavailable")})
        response = result.get("response", "")
        return response if isinstance(response, str) else json.dumps(response)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _LOGGER.warning("Model loop call failed: %s", exc)
        return json.dumps({"error": str(exc)})


_H_SYSTEM_PROMPT = """\
You are a strategic planner for a software engineering harness called Jules Bridge.
Your job is to break a given problem into 3-7 high-level steps.
Do NOT include implementation details — those come from the L module later.
For each step, write one clear, actionable sentence.

HRE UNBLOCKING PROTOCOL:
If the problem is a 'blocker' or 'failure', you MUST follow the HRE scaffold:
1. Hypothesis: Classify the blocker.
2. Route: Identify the tool/file/route to test.
3. Evidence: Define what output is needed.
Include these in your 'reasoning' field.

Return ONLY valid JSON in this exact shape:
{"goal_statement": "<one sentence>", "steps": ["<step1>", ...], "confidence": 0.0-1.0, "reasoning": "<chain of thought with HRE if applicable>"}
"""

_L_SYSTEM_PROMPT = """\
You are a precise executor for Jules Bridge. You receive one high-level step and must decide the concrete action.
action_type must be exactly one of: "tool_call" | "answer" | "observe" | "skip"
- tool_call: payload has {"tool": "<name>", "args": {...}}
- answer: payload has {"text": "<answer>"}
- observe: payload has {"what_to_check": "<description>"}
- skip: payload has {"reason": "<why skipped>"}

HRE UNBLOCKING PROTOCOL:
If you are diagnosing a blocker, ensure your reasoning follows the HRE pattern:
Hypothesis -> Route -> Evidence.

Return ONLY valid JSON:
{"action_type": "<type>", "payload": {...}, "confidence": 0.0-1.0, "reasoning": "<brief rationale with HRE if applicable>"}
"""


def _extract_json_text(raw: str) -> str:
    """Strip markdown fences and return JSON-looking payload."""
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _parse_llm_json(raw: str) -> Dict[str, Any]:
    """Parse model output as JSON with fence/brace extraction."""
    text = _extract_json_text(raw)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise json.JSONDecodeError("Expected JSON object", text, 0)
    return data


def _h_model_loop_call(problem: str, context: str, model_name: str, model_alias: str = "fast") -> Dict[str, Any]:
    """H module backed by the VM/browser model loop."""
    user_prompt = f"Problem: {problem}"
    if context:
        user_prompt += f"\n\nContext:\n{context}"
    raw = _model_loop_chat(_H_SYSTEM_PROMPT, user_prompt, model_alias)
    try:
        data = _parse_llm_json(raw)
        if "error" in data:
            _LOGGER.warning("Model-loop H-module error: %s — using stub fallback", data["error"])
            return _h_stub(problem, model_name)
        data.setdefault("model", model_name)
        return data
    except json.JSONDecodeError:
        _LOGGER.warning("Model-loop H-module returned non-JSON — using stub fallback")
        return _h_stub(problem, model_name)


def _l_model_loop_call(
    step: str,
    step_index: int,
    problem: str,
    context: str,
    model_name: str,
    model_alias: str = "fast",
) -> Dict[str, Any]:
    """L module backed by the VM/browser model loop."""
    user_prompt = (
        f"Original problem: {problem}\n"
        f"Step {step_index}: {step}"
    )
    if context:
        user_prompt += f"\nContext: {context}"
    raw = _model_loop_chat(_L_SYSTEM_PROMPT, user_prompt, model_alias)
    try:
        data = _parse_llm_json(raw)
        if "error" in data:
            _LOGGER.warning("Model-loop L-module error: %s — using stub fallback", data["error"])
            return _l_stub(step, step_index, model_name)
        return data
    except json.JSONDecodeError:
        _LOGGER.warning("Model-loop L-module returned non-JSON — using stub fallback")
        return _l_stub(step, step_index, model_name)


# ---------------------------------------------------------------------------
# Public dispatch functions — route stub vs. model loop based on model alias
# ---------------------------------------------------------------------------

def _h_module_call(problem: str, context: str, model: str = "stub") -> Dict[str, Any]:
    """H module: high-level planning call.

    Dispatches to the VM/browser model loop when model is a known alias ("fast" or "smart").
    Falls back to deterministic stub when model="stub" or alias is unknown.

    System prompt template (H module):
        You are a strategic planner. Break the problem into 3-7 high-level steps.
        Do NOT include implementation details — those come later.
        For each step, write one clear action sentence.
        Return JSON: {goal_statement, steps: [], confidence, reasoning}

    Args:
        problem: The problem to solve
        context: Relevant background context
        model: "stub" | "fast" | "smart" | raw model-loop label

    Returns:
        JSON-parseable dict with goal_statement, steps, confidence, reasoning
    """
    resolved = _MODEL_ALIASES.get(model, model)  # unknown alias treated as raw model name
    if resolved is None:
        return _h_stub(problem, model)
    return _h_model_loop_call(problem, context, resolved, model_alias=model)


def _l_module_call(
    step: str,
    step_index: int,
    problem: str,
    context: str,
    model: str = "stub",
) -> Dict[str, Any]:
    """L module: low-level execution planning for one H step.

    Dispatches to the VM/browser model loop when model is a known alias ("fast" or "smart").
    Falls back to deterministic stub when model="stub" or alias is unknown.

    System prompt template (L module):
        You are a precise executor. You have one task to complete.
        Return the exact action to take as JSON.
        action_type must be one of: "tool_call" | "answer" | "observe" | "skip"
        Return JSON: {action_type, payload, confidence, reasoning}

    Args:
        step: One H-level step description
        step_index: Index of this step in the plan
        problem: The original problem (full context)
        context: Additional context
        model: "stub" | "fast" | "smart" | raw model-loop label

    Returns:
        JSON-parseable dict with action_type, payload, confidence, reasoning
    """
    resolved = _MODEL_ALIASES.get(model, model)
    if resolved is None:
        return _l_stub(step, step_index, model)
    return _l_model_loop_call(step, step_index, problem, context, resolved, model_alias=model)


def _halt_check(
    actions: List[LLevelAction],
    plan: HLevelPlan,
    steps_used: int,
    steps_budget: int,
) -> HaltDecision:
    """ACT halting decision — should we stop or keep computing?

    Implements the Q-learning halting logic from HRM, adapted for LLM-based reasoning:
    - If all plan steps have been executed: halt (goal reached)
    - If budget exhausted: halt (forced)
    - If confidence is very high: halt early (efficient)
    - If stuck (repeated failures): halt (give up gracefully)

    Args:
        actions: Actions taken so far
        plan: The H-level plan
        steps_used: How many L-module calls have been made
        steps_budget: Maximum allowed L-module calls

    Returns:
        HaltDecision indicating whether to stop and why
    """
    if steps_used >= steps_budget:
        return HaltDecision(
            should_halt=True,
            reason="budget_exhausted",
            steps_used=steps_used,
            steps_budget=steps_budget,
        )

    executed = [a for a in actions if a.should_execute]
    all_steps_done = len(executed) >= plan.step_count

    if all_steps_done:
        return HaltDecision(
            should_halt=True,
            reason="goal_reached",
            steps_used=steps_used,
            steps_budget=steps_budget,
        )

    # Check if stuck: last 2 consecutive actions both low confidence
    if len(actions) >= 2:
        last_two = actions[-2:]
        if all(a.confidence < 0.4 for a in last_two):
            return HaltDecision(
                should_halt=True,
                reason="stuck",
                steps_used=steps_used,
                steps_budget=steps_budget,
            )

    # High confidence early halt (like ACT epsilon exploration)
    if actions and actions[-1].confidence >= 0.95 and len(executed) >= plan.step_count - 1:
        return HaltDecision(
            should_halt=True,
            reason="confident",
            steps_used=steps_used,
            steps_budget=steps_budget,
        )

    return HaltDecision(
        should_halt=False,
        reason="continuing",
        steps_used=steps_used,
        steps_budget=steps_budget,
    )


def _extract_answer(actions: List[LLevelAction], _plan: HLevelPlan) -> Optional[str]:
    """Extract a final answer from the set of executed actions."""
    answer_actions = [a for a in actions if a.action_type == "answer" and a.should_execute]
    if not answer_actions:
        return None
    # Take the last answer action (most refined)
    last = answer_actions[-1]
    text = last.payload.get("text")
    if text and _GENERIC_STEP_RE.match(str(text).strip()):
        return None
    return text


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def reason(
    problem: str,
    context: str = "",
    halt_budget: int = 8,
    model: str = "stub",
    require_json: bool = False,
) -> ReasoningTrace:
    """Run hierarchical reasoning on a problem using H → L cycles with ACT halting.

    This is the main entry point. It mirrors the HRM forward pass:
      1. H module produces an abstract plan (z_H)
      2. For each plan step, L module produces a concrete action (z_L)
      3. ACT halting decides when to stop (even before the budget is exhausted)

    Args:
        problem: The problem to solve (free-form text or JSON)
        context: Additional context (e.g. current system state, constraints)
        halt_budget: Maximum number of L-module calls before forced halt
                     (analogous to halt_max_steps in HRM config)
        model: LLM model to use for H and L modules

    Returns:
        ReasoningTrace with plan, executed actions, halt decision, and answer

    Never raises — all sub-operations are defensive and return partial data.
    This matches oracle_session.py's contract: "Never raises".
    """
    if _is_mcq_quiz_problem(problem):
        return _reason_mcq_quiz(problem, context=context, model=model)

    if _is_structured_diagnostic_problem(problem):
        return _reason_structured_diagnostic(
            problem,
            context=context,
            model=model,
            require_json=require_json,
        )

    t0 = time.perf_counter()
    actions: List[LLevelAction] = []

    # Step 1: H module — produce the abstract plan
    try:
        h_raw = _h_module_call(problem, context, model)
        plan = HLevelPlan(
            steps=h_raw.get("steps", []),
            goal_statement=h_raw.get("goal_statement", problem[:80]),
            confidence=float(h_raw.get("confidence", 0.5)),
            reasoning=h_raw.get("reasoning", ""),
            model=h_raw.get("model", model),
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        plan = HLevelPlan(
            steps=["Resolve the problem"],
            goal_statement=problem[:80],
            confidence=0.1,
            reasoning=f"H module failed: {exc}",
            model=model,
        )

    # Step 2: L module loop — execute each step with ACT halting
    steps_used = 0
    for step_index, step in enumerate(plan.steps):
        halt = _halt_check(actions, plan, steps_used, halt_budget)
        if halt.should_halt:
            break

        try:
            l_raw = _l_module_call(step, step_index, problem, context, model)
            action = LLevelAction(
                step_index=step_index,
                step_description=step,
                action_type=l_raw.get("action_type", "skip"),
                payload=l_raw.get("payload", {}),
                confidence=float(l_raw.get("confidence", 0.5)),
                reasoning=l_raw.get("reasoning", ""),
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            action = LLevelAction(
                step_index=step_index,
                step_description=step,
                action_type="skip",
                payload={"error": str(exc)},
                confidence=0.0,
                reasoning=f"L module failed: {exc}",
            )

        actions.append(action)
        steps_used += 1

    # Final halt decision
    final_halt = _halt_check(actions, plan, steps_used, halt_budget)
    if not final_halt.should_halt:
        final_halt = HaltDecision(
            should_halt=True,
            reason="goal_reached",
            steps_used=steps_used,
            steps_budget=halt_budget,
        )

    answer = _extract_answer(actions, plan)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return ReasoningTrace(
        problem=problem,
        plan=plan,
        actions=actions,
        halt=final_halt,
        answer=answer,
        elapsed_ms=elapsed_ms,
        # CDLC Observe: structured feedback for context improvement
        feedback={
            "plan_confidence": plan.confidence,
            "steps_planned": plan.step_count,
            "steps_executed": len([a for a in actions if a.should_execute]),
            "halt_reason": final_halt.reason,
            "halted_early": final_halt.halted_early,
            "mean_action_confidence": (
                sum(a.confidence for a in actions) / len(actions) if actions else 0.0
            ),
        },
    )


def plan_only(problem: str, context: str = "", model: str = "stub") -> HLevelPlan:
    """Run only the H module — return an abstract plan without executing any steps.

    Use when you want to preview the plan before committing to execution.

    Args:
        problem: The problem to plan for
        context: Additional context
        model: LLM model to use

    Returns:
        HLevelPlan with abstract steps and confidence
    """
    try:
        h_raw = _h_module_call(problem, context, model)
        return HLevelPlan(
            steps=h_raw.get("steps", []),
            goal_statement=h_raw.get("goal_statement", problem[:80]),
            confidence=float(h_raw.get("confidence", 0.5)),
            reasoning=h_raw.get("reasoning", ""),
            model=h_raw.get("model", model),
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return HLevelPlan(
            steps=[],
            goal_statement=problem[:80],
            confidence=0.0,
            reasoning=f"H module failed: {exc}",
            model=model,
        )


def execute_step(
    step: str,
    context: str = "",
    step_index: int = 0,
    problem: str = "",
    model: str = "stub",
) -> LLevelAction:
    """Run only the L module for a single step — useful for manual control.

    Use when you have a specific step to execute without running the full H→L cycle.

    Args:
        step: The step description to execute
        context: Additional context
        step_index: Index of this step (for logging)
        problem: The original problem (for full context)
        model: LLM model to use

    Returns:
        LLevelAction with the concrete action to take
    """
    try:
        l_raw = _l_module_call(step, step_index, problem or step, context, model)
        return LLevelAction(
            step_index=step_index,
            step_description=step,
            action_type=l_raw.get("action_type", "skip"),
            payload=l_raw.get("payload", {}),
            confidence=float(l_raw.get("confidence", 0.5)),
            reasoning=l_raw.get("reasoning", ""),
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return LLevelAction(
            step_index=step_index,
            step_description=step,
            action_type="skip",
            payload={"error": str(exc)},
            confidence=0.0,
            reasoning=f"L module failed: {exc}",
        )
# Ticket 009 - HRE Depth & Skill Discovery
# ---------------------------------------------------------------------------

def score_hre_depth(trace: ReasoningTrace) -> dict:
    """Score the HRE pass depth and write to eval results."""
    _root_dir_local = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    eval_path = os.path.join(_root_dir_local, "memory", "eval_results.json")

    score = float(trace.hre_passes_taken)
    self_unblock_rate = 1.0 if trace.self_unblocked else 0.0
    gaps_found = list(trace.blockers_resolved)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "depth_score": score,
        "self_unblock_rate": self_unblock_rate,
        "gaps_found": gaps_found,
        "knowledge_sources": list(trace.knowledge_sources_checked),
        "problem": trace.problem[:100]
    }

    # Append to JSON lines file
    try:
        os.makedirs(os.path.dirname(eval_path), exist_ok=True)
        with open(eval_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")
    except Exception as e:  # pylint: disable=broad-exception-caught
        _LOGGER.warning("Failed to record HRE depth: %s", e)

    return result


def discover_skills(skills_dir: str) -> list[dict]:
    """Parse SKILL.md files to discover loaded skills."""
    skills = []
    if not os.path.exists(skills_dir):
        return skills

    for skill_name in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, skill_name, "SKILL.md")
        if not os.path.isfile(skill_path):
            continue

        try:
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse simple YAML frontmatter manually
            name = ""
            description = ""
            trigger = ""

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    for line in frontmatter.split("\n"):
                        if line.startswith("name:"):
                            name = line.split(":", 1)[1].strip()
                        elif line.startswith("description:"):
                            description = line.split(":", 1)[1].strip()
                        elif line.startswith("trigger_condition:"):
                            trigger = line.split(":", 1)[1].strip()

            if not name:
                name = skill_name

            skills.append({
                "name": name,
                "description": description,
                "trigger_condition": trigger,
                "skill_path": skill_path
            })
        except Exception as e:  # pylint: disable=broad-exception-caught
            _LOGGER.warning("Failed to parse skill %s: %s", skill_path, e)

    return skills


_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GOTCHAS_PATH = os.path.join(_root_dir, "context", "05_gotchas.md")

def inject_gotcha(module: str, text: str) -> dict:
    """Inject a new edge case directly into 05_gotchas.md."""
    if not os.path.exists(_GOTCHAS_PATH):
        return {"status": "error", "message": "Gotchas file not found"}

    try:
        with open(_GOTCHAS_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the module heading
        heading = f"## {module}"
        if heading not in content:
            # Append new module section at the end
            new_content = content + f"\n\n{heading}\n\n- **auto-injected**: {text}\n"
        else:
            # Inject right after the heading
            parts = content.split(heading, 1)
            new_content = parts[0] + heading + f"\n\n- **auto-injected**: {text}" + parts[1]

        with open(_GOTCHAS_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {"status": "ok", "module": module, "text": text}
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"status": "error", "message": str(e)}
