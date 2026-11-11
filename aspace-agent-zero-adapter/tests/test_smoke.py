"""Smoke — the loop runs end to end without the fork (H-P5-2, H-P5-10).

A stub model drives the loop: first a tool call, then an explicit
``break_loop`` response. Free text alone must never complete a turn.
"""

import json

from aspace_agent_zero_adapter import AspaceAgentLoop, LoopState


def _model_tool_then_break():
    calls = {"n": 0}

    def model(messages):
        calls["n"] += 1
        if calls["n"] == 1:
            return '```json\n{"tool": "echo", "args": {"text": "hello"}}\n```'
        return '```json\n{"tool": "break_loop", "args": {"response": "done: hello"}}\n```'

    return model


def test_smoke_loop_tool_then_break():
    loop = AspaceAgentLoop(number=0)
    result = loop.turn(
        "say hello",
        _model_tool_then_break(),
        tools={"echo": lambda args: args["text"]},
    )
    assert result == "done: hello"
    assert loop.state is LoopState.DONE
    kinds = [e.kind for e in loop.history]
    assert "tool_result" in kinds
    assert loop.history[-1].kind == "ai_response"


def test_smoke_free_text_never_completes():
    """Free text is generation thoughts; the loop guard ends the turn."""
    loop = AspaceAgentLoop(number=0)
    result = loop.turn("talk", lambda messages: "just some prose, no tool")
    assert result == ""
    assert loop.state is LoopState.DONE
    assert loop.loop_data.iteration == 25  # MAX_ITERATIONS guard


def test_smoke_malformed_tool_keeps_repair_path():
    calls = {"n": 0}

    def model(messages):
        calls["n"] += 1
        if calls["n"] == 1:
            return '```json\n{"tool": 42}\n```'  # malformed: tool not a string
        return '```json\n{"tool": "break_loop", "args": {"response": "repaired"}}\n```'

    loop = AspaceAgentLoop(number=0)
    result = loop.turn("fix me", model)
    assert result == "repaired"
    assert any(e.kind == "warning" for e in loop.history)


def test_smoke_unknown_tool_is_a_result_not_a_crash():
    calls = {"n": 0}

    def model(messages):
        calls["n"] += 1
        if calls["n"] == 1:
            return '```json\n{"tool": "nope", "args": {}}\n```'
        return '```json\n{"tool": "break_loop", "args": {"response": "ok"}}\n```'

    loop = AspaceAgentLoop(number=0)
    result = loop.turn("unknown", model)
    assert result == "ok"
    assert any("unknown tool" in e.content for e in loop.history)


def test_smoke_ai_response_owns_state_advancement():
    loop = AspaceAgentLoop(number=0)
    entry = loop.hist_add_ai_response(
        "hi", llm_result={"response_id": "resp_123"}
    )
    assert entry.response_id == "resp_123"
    assert loop.data["responses_state"]["response_id"] == "resp_123"
    assert loop.data["responses_state"]["history_counter"] == 1


def test_smoke_snapshot_is_fork_free():
    loop = AspaceAgentLoop(number=0)
    loop.hist_add_user_message("hi")
    snap = loop.snapshot()
    assert snap["agent"] == "A0"
    assert snap["history"][0] == {"role": "user", "content": "hi", "kind": "message"}
    # No fork module path leaks into the persisted snapshot.
    dumped = json.dumps(snap)
    assert "agent.py" not in dumped
    assert "models.py" not in dumped
