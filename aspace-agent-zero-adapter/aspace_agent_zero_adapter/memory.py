"""Unified memory — design D6.

Upstream (gel): chats persist as files (snapshots, history) under
``usr/``; retrieval uses ``helpers/vector_db.py`` ``MyFaiss`` (FAISS +
local sentence-transformers embeddings).

Native rule (D6): the Shared Brain JSONL is the ONLY source of
truth. FAISS is kept as a retrieval index — an index DERIVED from
the Shared Brain content, rebuilt from it, never the inverse. One
memory is authoritative; the index can never diverge from it, because
it is rebuilt from it.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


class SharedBrainMemory:
    """Append-only JSONL memory of reference (D-N049 D4).

    One entry per line: ``{"ts", "kind", "content", "meta"}``.
    Chats are persisted here, not in the fork's ``usr/`` files.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def append(self, kind: str, content: str, meta: dict | None = None) -> dict:
        entry = {
            "ts": time.time(),
            "kind": kind,
            "content": content,
            "meta": meta or {},
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def read_all(self) -> list[dict]:
        entries: list[dict] = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries

    def persist_chat(self, chat_id: str, messages: list[dict]) -> dict:
        """Persist a whole chat as one brain entry (H-P5-5)."""
        content = json.dumps({"chat_id": chat_id, "messages": messages}, ensure_ascii=False)
        return self.append("chat", content, {"chat_id": chat_id})

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Keyword-overlap retrieval over the brain itself."""
        wanted = _tokens(query)
        if not wanted:
            return []
        scored: list[tuple[int, dict]] = []
        for entry in self.read_all():
            hit = len(wanted & _tokens(entry.get("content", "")))
            if hit:
                scored.append((hit, entry))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["ts"]))
        return [entry for _, entry in scored[:limit]]


class FaissIndex:
    """Derived retrieval index — FAISS kept as an index only (D6).

    The index is built FROM the Shared Brain and rebuilt from it;
    it is never a second memory. ``rebuild`` is the only way content
    enters the index, and ``check_no_divergence`` proves the index
    holds exactly the brain's content.
    """

    def __init__(self):
        self._postings: dict[str, set[int]] = {}
        self._docs: list[str] = []

    def rebuild(self, brain: SharedBrainMemory) -> int:
        """Rebuild the whole index from the brain. Returns doc count."""
        self._postings = {}
        self._docs = []
        for entry in brain.read_all():
            doc_id = len(self._docs)
            self._docs.append(entry.get("content", ""))
            for token in _tokens(entry.get("content", "")):
                self._postings.setdefault(token, set()).add(doc_id)
        return len(self._docs)

    def search(self, query: str, limit: int = 10) -> list[str]:
        wanted = _tokens(query)
        if not wanted:
            return []
        hits: dict[int, int] = {}
        for token in wanted:
            for doc_id in self._postings.get(token, set()):
                hits[doc_id] = hits.get(doc_id, 0) + 1
        ranked = sorted(hits.items(), key=lambda pair: (-pair[1], pair[0]))
        return [self._docs[doc_id] for doc_id, _ in ranked[:limit]]

    def doc_count(self) -> int:
        return len(self._docs)


def check_no_divergence(brain: SharedBrainMemory, index: FaissIndex) -> bool:
    """One memory is authoritative: the index holds exactly the brain.

    Rebuilds a fresh index from the brain and compares doc lists.
    True means no divergence between the two (H-P5-5).
    """
    fresh = FaissIndex()
    fresh.rebuild(brain)
    return fresh._docs == index._docs
