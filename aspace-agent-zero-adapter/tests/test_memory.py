"""Memory — Shared Brain JSONL is the truth, FAISS the index (H-P5-5, D6)."""

from aspace_agent_zero_adapter import FaissIndex, SharedBrainMemory, check_no_divergence


def test_brain_append_and_read(tmp_path):
    brain = SharedBrainMemory(tmp_path / "memory.jsonl")
    brain.append("note", "the runtime runs without the original")
    brain.append("chat", "hello world")
    entries = brain.read_all()
    assert len(entries) == 2
    assert entries[0]["kind"] == "note"
    assert entries[1]["content"] == "hello world"


def test_brain_search_keyword_overlap(tmp_path):
    brain = SharedBrainMemory(tmp_path / "memory.jsonl")
    brain.append("note", "the runtime runs without the original")
    brain.append("note", "unrelated weather report")
    hits = brain.search("runtime original")
    assert len(hits) == 1
    assert "runtime" in hits[0]["content"]


def test_persist_chat_roundtrip(tmp_path):
    brain = SharedBrainMemory(tmp_path / "memory.jsonl")
    messages = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    brain.persist_chat("chat-1", messages)
    entries = brain.read_all()
    assert entries[0]["meta"]["chat_id"] == "chat-1"


def test_faiss_index_is_derived_from_brain(tmp_path):
    brain = SharedBrainMemory(tmp_path / "memory.jsonl")
    brain.append("note", "the runtime runs without the original")
    brain.append("note", "the daemon is single")
    index = FaissIndex()
    assert index.rebuild(brain) == 2
    assert index.search("runtime") == ["the runtime runs without the original"]
    assert index.search("daemon") == ["the daemon is single"]
    assert index.search("nothing here") == []


def test_no_divergence_between_brain_and_index(tmp_path):
    brain = SharedBrainMemory(tmp_path / "memory.jsonl")
    brain.append("note", "first entry")
    brain.append("note", "second entry")
    index = FaissIndex()
    index.rebuild(brain)
    assert check_no_divergence(brain, index) is True
    # Appending to the brain without rebuilding diverges until rebuilt.
    brain.append("note", "third entry")
    assert check_no_divergence(brain, index) is False
    index.rebuild(brain)
    assert check_no_divergence(brain, index) is True
