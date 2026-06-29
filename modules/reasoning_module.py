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
import subprocess
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

_LOGGER = logging.getLogger("jules_bridge.reasoning")

# ---------------------------------------------------------------------------
# Model alias table — callers use aliases, not raw provider model strings
# ---------------------------------------------------------------------------
# Swap the right-hand values to change models without touching call sites.
_MODEL_ALIASES: Dict[str, Optional[str]] = {
    "stub":  None,                    # deterministic stub — for unit tests
    "fast":  "gemini-2.0-flash",      # cheap, fast reasoning (Gemini fallback)
    "smart": "gemini-2.5-pro",        # high-quality planning (Gemini fallback)
}

_OPENROUTER_MODEL_ALIASES: Dict[str, str] = {
    # Reliable free-tier models on OpenRouter (updated 2026-06)
    # gemma-4 free models are frequently rate-limited; deepseek-r1 is stable
    "fast": "deepseek/deepseek-r1-0528:free",
    "smart": "deepseek/deepseek-r1-0528:free",
}

_OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


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

    # CDLC Observe: structured feedback for improving future context
    feedback: Dict[str, Any] = field(default_factory=dict)

    # HRE Depth Tracking
    hre_passes_taken: int = 1
    self_unblocked: bool = False
    blockers_resolved: List[str] = field(default_factory=list)
    knowledge_sources_checked: List[str] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
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


def _l_stub(_step: str, step_index: int, _model: str) -> Dict[str, Any]:
    """Deterministic L-module stub for unit tests."""
    return {
        "action_type": "answer",
        "payload": {"text": f"Executed action for step {step_index}"},
        "confidence": 0.7,
        "reasoning": "[L module stub — replace with real LLM call]",
    }


# ---------------------------------------------------------------------------
# LLM helpers — OpenRouter (preferred) then Gemini when model != "stub"
# ---------------------------------------------------------------------------

def _load_env_keys() -> None:
    try:
        from notify_email import load_env  # pylint: disable=import-outside-toplevel

        load_env()
    except ImportError:
        pass


def _openrouter_api_keys() -> List[str]:
    """Return configured OpenRouter keys in rotation order."""
    _load_env_keys()
    keys: List[str] = []
    multi = os.environ.get("OPENROUTER_API_KEYS", "").strip()
    if multi:
        keys.extend(part.strip() for part in multi.split(",") if part.strip())
    single = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if single and single not in keys:
        keys.insert(0, single)
    return keys


def _resolve_model_name(model: str, use_openrouter: bool) -> str:
    if use_openrouter:
        if model in _OPENROUTER_MODEL_ALIASES:
            return _OPENROUTER_MODEL_ALIASES[model]
        if model in _MODEL_ALIASES and _MODEL_ALIASES[model]:
            return _OPENROUTER_MODEL_ALIASES.get("fast", model)
    resolved = _MODEL_ALIASES.get(model, model)
    if resolved is None:
        return model
    return resolved


def _openrouter_chat(system_prompt: str, user_prompt: str, model_name: str) -> str:
    """Call OpenRouter chat completions; rotate keys on rate-limit errors."""
    keys = _openrouter_api_keys()
    if not keys:
        return json.dumps({"error": "OPENROUTER_API_KEY not set"})

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {keys[0]}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:5000",
        "X-Title": "Jules Bridge",
    }

    last_error = "OpenRouter request failed"
    for key in keys:
        headers["Authorization"] = f"Bearer {key}"
        try:
            response = requests.post(
                _OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
            if response.status_code == 429 and len(keys) > 1:
                last_error = "OpenRouter rate limited"
                continue
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                last_error = str(data["error"])
                continue
            content = data["choices"][0]["message"]["content"]
            return content if isinstance(content, str) else json.dumps(content)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            last_error = str(exc)
            _LOGGER.warning("OpenRouter call failed with key rotation: %s", exc)

    return json.dumps({"error": last_error})


def _llm_chat(system_prompt: str, user_prompt: str, model_name: str, model_alias: str) -> str:
    """Prefer OpenRouter free models; fall back to Vertex AI Gemini (via ADC) on error."""
    if _openrouter_api_keys():
        resolved = _resolve_model_name(model_alias, use_openrouter=True)
        raw = _openrouter_chat(system_prompt, user_prompt, resolved)
        try:
            data = json.loads(raw)
            if "error" not in data:
                return raw
            _LOGGER.warning("OpenRouter error: %s — trying Vertex AI Gemini fallback", data["error"])
        except json.JSONDecodeError:
            if raw and not raw.startswith("{"):
                return raw
    return _gemini_chat(system_prompt, user_prompt, model_name)


def _gcloud_access_token() -> str:
    """Return a fresh OAuth2 bearer token via `gcloud auth print-access-token`.

    Uses the interactive gcloud login (ya29.*) which has full API scopes,
    including generativelanguage.googleapis.com. Returns empty string on failure.
    On Windows, gcloud is a .cmd batch file so shell=True is required.
    """
    for cmd in (["gcloud", "auth", "print-access-token"], ["gcloud.cmd", "auth", "print-access-token"]):
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15, shell=True, check=False,
            )
            token = result.stdout.strip()
            if result.returncode == 0 and token.startswith("ya29"):
                return token
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            continue
    _LOGGER.warning("gcloud token fetch failed — ensure gcloud is installed and `gcloud auth login` has been run")
    return ""


def _gemini_chat(system_prompt: str, user_prompt: str, model_name: str) -> str:
    """Call Gemini via the Generative Language REST API using a gcloud OAuth2 token.

    No API key required — uses `gcloud auth print-access-token` (the interactive
    gcloud login token which has full API scopes).  Falls back to a JSON error
    string if gcloud is unavailable or the call fails.
    """
    token = _gcloud_access_token()
    if not token:
        _LOGGER.warning("No gcloud token available; cannot call Gemini")
        return json.dumps({"error": "gcloud auth token unavailable — run: gcloud auth login"})

    _load_env_keys()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _LOGGER.error("Gemini REST call failed: %s", exc)
        return json.dumps({"error": str(exc)})


_H_SYSTEM_PROMPT = """\
You are a strategic planner for a software engineering harness called Jules Bridge.
Your job is to break a given problem into 3-7 high-level steps.
Do NOT include implementation details — those come from the L module later.
For each step, write one clear, actionable sentence.
Return ONLY valid JSON in this exact shape:
{"goal_statement": "<one sentence>", "steps": ["<step1>", ...], "confidence": 0.0-1.0, "reasoning": "<chain of thought>"}
"""

_L_SYSTEM_PROMPT = """\
You are a precise executor for Jules Bridge. You receive one high-level step and must decide the concrete action.
action_type must be exactly one of: "tool_call" | "answer" | "observe" | "skip"
- tool_call: payload has {"tool": "<name>", "args": {...}}
- answer: payload has {"text": "<answer>"}
- observe: payload has {"what_to_check": "<description>"}
- skip: payload has {"reason": "<why skipped>"}
Return ONLY valid JSON:
{"action_type": "<type>", "payload": {...}, "confidence": 0.0-1.0, "reasoning": "<brief rationale>"}
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


def _h_gemini_call(problem: str, context: str, model_name: str, model_alias: str = "fast") -> Dict[str, Any]:
    """H module backed by OpenRouter or Gemini."""
    user_prompt = f"Problem: {problem}"
    if context:
        user_prompt += f"\n\nContext:\n{context}"
    raw = _llm_chat(_H_SYSTEM_PROMPT, user_prompt, model_name, model_alias)
    try:
        data = _parse_llm_json(raw)
        if "error" in data:
            _LOGGER.warning("Gemini H-module error: %s — using stub fallback", data["error"])
            return _h_stub(problem, model_name)
        data.setdefault("model", model_name)
        return data
    except json.JSONDecodeError:
        _LOGGER.warning("Gemini H-module returned non-JSON — using stub fallback")
        return _h_stub(problem, model_name)


def _l_gemini_call(
    step: str,
    step_index: int,
    problem: str,
    context: str,
    model_name: str,
    model_alias: str = "fast",
) -> Dict[str, Any]:
    """L module backed by OpenRouter or Gemini."""
    user_prompt = (
        f"Original problem: {problem}\n"
        f"Step {step_index}: {step}"
    )
    if context:
        user_prompt += f"\nContext: {context}"
    raw = _llm_chat(_L_SYSTEM_PROMPT, user_prompt, model_name, model_alias)
    try:
        data = _parse_llm_json(raw)
        if "error" in data:
            _LOGGER.warning("Gemini L-module error: %s — using stub fallback", data["error"])
            return _l_stub(step, step_index, model_name)
        return data
    except json.JSONDecodeError:
        _LOGGER.warning("Gemini L-module returned non-JSON — using stub fallback")
        return _l_stub(step, step_index, model_name)


# ---------------------------------------------------------------------------
# Public dispatch functions — route stub vs. Gemini based on model alias
# ---------------------------------------------------------------------------

def _h_module_call(problem: str, context: str, model: str = "stub") -> Dict[str, Any]:
    """H module: high-level planning call.

    Dispatches to Gemini when model is a known alias ("fast" or "smart").
    Falls back to deterministic stub when model="stub" or alias is unknown.

    System prompt template (H module):
        You are a strategic planner. Break the problem into 3-7 high-level steps.
        Do NOT include implementation details — those come later.
        For each step, write one clear action sentence.
        Return JSON: {goal_statement, steps: [], confidence, reasoning}

    Args:
        problem: The problem to solve
        context: Relevant background context
        model: "stub" | "fast" | "smart" | raw Gemini model string

    Returns:
        JSON-parseable dict with goal_statement, steps, confidence, reasoning
    """
    resolved = _MODEL_ALIASES.get(model, model)  # unknown alias treated as raw model name
    if resolved is None:
        return _h_stub(problem, model)
    return _h_gemini_call(problem, context, resolved, model_alias=model)


def _l_module_call(
    step: str,
    step_index: int,
    problem: str,
    context: str,
    model: str = "stub",
) -> Dict[str, Any]:
    """L module: low-level execution planning for one H step.

    Dispatches to Gemini when model is a known alias ("fast" or "smart").
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
        model: "stub" | "fast" | "smart" | raw Gemini model string

    Returns:
        JSON-parseable dict with action_type, payload, confidence, reasoning
    """
    resolved = _MODEL_ALIASES.get(model, model)
    if resolved is None:
        return _l_stub(step, step_index, model)
    return _l_gemini_call(step, step_index, problem, context, resolved, model_alias=model)


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
    return last.payload.get("text")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def reason(
    problem: str,
    context: str = "",
    halt_budget: int = 8,
    model: str = "stub",
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
