"""Agent loop — mirror of agent.py:364 ``Agent`` (gel ba9b67d).

The loop, re-implemented, not copied:
  message -> model -> tools -> memory -> response

Rules carried from the upstream DOX (agent-zero-repo/AGENTS.md):
- Message-loop completion requires an explicit response-tool call with
  ``break_loop``. Free text in either transport remains generation
  thoughts and silently continues; never synthesize a response-tool
  call from prose.
- Malformed tool intent keeps its repair path (returned, not raised
  out of the turn).
- ``hist_add_ai_response`` owns Responses-API state advancement: it
  calls the internal state-remembering step itself. Callers must not
  invoke it manually.
- ``call_chat_model_turn`` builds native function tools only when the
  chat model's ``a0_api_mode`` selects Responses; Chat Completions
  turns pass an empty tool list.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum

MAX_ITERATIONS = 25
RESPONSE_TOOL_BREAK = "break_loop"


class LoopState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    RESPONDING = "responding"
    DONE = "done"
    INTERVENTION = "intervention"


@dataclass
class LoopData:
    """Per-turn loop data — mirror of agent.py:344 ``LoopData``."""

    user_message: str | None = None
    iteration: int = 0
    params_temporary: dict = field(default_factory=dict)


def extract_tool_request(text: str) -> dict | None:
    """Extract a tool request from model text.

    Wire format (adapter contract): a fenced JSON block carrying
    ``{"tool": <name>, "args": {...}}``. Returns None when no such
    block is present — free text is generation thoughts, never a
    synthesized tool call.
    """
    start = text.find("```json")
    if start == -1:
        start = text.find("```")
    if start == -1:
        return None
    body_start = text.find("\n", start)
    if body_start == -1:
        return None
    end = text.find("```", body_start + 1)
    if end == -1:
        return None
    try:
        parsed = json.loads(text[body_start + 1 : end].strip())
    except json.JSONDecodeError:
        return None
    # Return any dict carrying a "tool" key, even malformed: validation
    # owns the repair path, extraction must not swallow it.
    if isinstance(parsed, dict) and "tool" in parsed:
        return parsed
    return None


def validate_tool_request(request: dict) -> tuple[bool, str]:
    """Validate a tool request; malformed intent keeps its repair path.

    Returns (ok, repair_message). ``ok`` is False when the request is
    not a dict, has no string ``tool`` name, or has non-dict ``args``.
    The repair message is what the loop feeds back to the model.
    """
    if not isinstance(request, dict):
        return False, "Tool request must be a JSON object with 'tool' and 'args'."
    if not isinstance(request.get("tool"), str) or not request["tool"]:
        return False, "Tool request is missing a string 'tool' name."
    if "args" in request and not isinstance(request["args"], dict):
        return False, "Tool request 'args' must be a JSON object."
    return True, ""


@dataclass
class HistoryEntry:
    role: str  # user | assistant | tool | warning
    content: str
    kind: str = "message"  # message | ai_response | tool_result | warning
    tool_name: str = ""
    response_id: str = ""


class AspaceAgentLoop:
    """The Agent loop, native. Mirrors ``Agent`` (agent.py:364).

    ``model`` is a callable ``(messages) -> str`` supplied by the
    caller (the provider). ``tools`` maps tool names to callables
    ``(args) -> str``. The loop never calls the fork: agent.py and
    models.py are absent from the execution path (H-P5-2).
    """

    DATA_NAME_RESPONSES_STATE = "responses_state"

    def __init__(self, number: int = 0, config: dict | None = None):
        self.number = number
        self.agent_name = f"A{self.number}"
        self.config = config or {}
        self.history: list[HistoryEntry] = []
        self.data: dict = {}
        self.state = LoopState.IDLE
        self.last_user_message: str | None = None
        self.loop_data = LoopData()

    # -- history (mirror of Agent.hist_add_*; agent.py:725-830) --------

    def hist_add_message(self, role: str, content: str) -> HistoryEntry:
        entry = HistoryEntry(role=role, content=content)
        self.history.append(entry)
        return entry

    def hist_add_user_message(self, message: str, intervention: bool = False) -> HistoryEntry:
        self.last_user_message = message
        if intervention:
            self.state = LoopState.INTERVENTION
        return self.hist_add_message("user", message)

    def hist_add_ai_response(self, content: str, llm_result: dict | None = None) -> HistoryEntry:
        """Owns Responses-API state advancement (upstream rule).

        When the model turn passes an LLMResult carrying a response id,
        the state is remembered here, internally. Callers must not
        invoke the remembering step manually.
        """
        entry = HistoryEntry(role="assistant", content=content, kind="ai_response")
        self.history.append(entry)
        if llm_result and isinstance(llm_result.get("response_id"), str):
            entry.response_id = llm_result["response_id"]
            self._remember_llm_result_state(llm_result)
        return entry

    def _remember_llm_result_state(self, llm_result: dict) -> None:
        self.data[self.DATA_NAME_RESPONSES_STATE] = {
            "response_id": llm_result.get("response_id", ""),
            "history_counter": len(self.history),
        }

    def hist_add_warning(self, message: str, warning_id: str = "") -> HistoryEntry:
        entry = HistoryEntry(role="assistant", content=message, kind="warning")
        self.history.append(entry)
        return entry

    def hist_add_tool_result(self, tool_name: str, tool_result: str, **kwargs) -> HistoryEntry:
        entry = HistoryEntry(
            role="tool", content=tool_result, kind="tool_result", tool_name=tool_name
        )
        self.history.append(entry)
        return entry

    # -- prompt ---------------------------------------------------------

    def prepare_prompt(self) -> list[dict]:
        """System + history, in model order (mirror of prepare_prompt)."""
        messages: list[dict] = []
        system = self.config.get("system_prompt", "You are A0, the native agent engine.")
        messages.append({"role": "system", "content": system})
        for entry in self.history:
            messages.append({"role": entry.role, "content": entry.content})
        return messages

    # -- the loop -------------------------------------------------------

    def turn(self, user_message: str, model, tools: dict | None = None) -> str:
        """One user turn: message -> model -> tools -> memory -> response.

        ``model`` is called as ``model(messages) -> str``. ``tools``
        maps names to ``(args) -> str`` callables. Returns the final
        assistant response text. The loop completes only on an explicit
        response-tool call carrying ``break_loop``.
        """
        tools = tools or {}
        self.hist_add_user_message(user_message)
        self.loop_data = LoopData(user_message=user_message)
        self.state = LoopState.THINKING
        final_response = ""

        while self.loop_data.iteration < MAX_ITERATIONS:
            self.loop_data.iteration += 1
            self.loop_data.params_temporary = {}
            prompt = self.prepare_prompt()
            text = model(prompt)
            request = extract_tool_request(text)

            if request is None:
                # Free text is generation thoughts; silently continue.
                self.state = LoopState.THINKING
                continue

            ok, repair = validate_tool_request(request)
            if not ok:
                # Malformed tool intent keeps its repair path.
                self.hist_add_warning(repair)
                self.state = LoopState.THINKING
                continue

            tool_name = request["tool"]
            args = request.get("args", {})
            if tool_name == RESPONSE_TOOL_BREAK:
                final_response = str(args.get("response", ""))
                self.hist_add_ai_response(final_response)
                self.state = LoopState.DONE
                return final_response

            self.state = LoopState.TOOL_CALL
            handler = tools.get(tool_name)
            if handler is None:
                self.hist_add_tool_result(
                    tool_name, f"error: unknown tool '{tool_name}'"
                )
                continue
            try:
                result = handler(args)
            except Exception as exc:  # tool errors are results, not crashes
                result = f"error: {type(exc).__name__}: {exc}"
            self.hist_add_tool_result(tool_name, str(result))
            self.state = LoopState.THINKING

        # Iteration guard reached without an explicit break_loop.
        self.hist_add_warning(
            f"loop guard: {MAX_ITERATIONS} iterations without break_loop"
        )
        self.state = LoopState.DONE
        return final_response

    def snapshot(self) -> dict:
        """Chat persistence shape: history + state, no fork involved."""
        return {
            "agent": self.agent_name,
            "state": self.state.value,
            "iterations": self.loop_data.iteration,
            "history": [
                {"role": e.role, "content": e.content, "kind": e.kind}
                for e in self.history
            ],
            "created_at": time.time(),
        }
