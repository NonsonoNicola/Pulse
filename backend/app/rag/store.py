from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from app.core.config import KNOWLEDGE_DIR, load_mission
from app.core.db import Database, dumps, loads

TOKEN_RE = re.compile(r"[a-zA-ZàèéìòùÀÈÉÌÒÙ0-9]+")
STOPWORDS = {
    "the",
    "and",
    "or",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "is",
    "are",
    "be",
    "as",
    "at",
    "by",
    "from",
    "this",
    "that",
    "it",
    "its",
    "di",
    "e",
    "il",
    "la",
    "le",
    "gli",
    "un",
    "una",
    "per",
    "con",
    "che",
    "non",
    "del",
    "della",
}
DIM = 384


def tokenize(text: str) -> list[str]:
    raw = [t.lower() for t in TOKEN_RE.findall(text)]
    tokens: list[str] = []
    for token in raw:
        if token in STOPWORDS or len(token) < 2:
            continue
        tokens.append(token)
        if len(token) > 4:
            tokens.extend(token[i : i + 3] for i in range(len(token) - 2))
    return tokens


def embed(tokens: list[str]) -> list[float]:
    vector = [0.0] * DIM
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % DIM
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [round(v / norm, 6) for v in vector]


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    return meta, parts[2].strip()


def split_sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = "Overview"
    current: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current:
                text = "\n".join(current).strip()
                if text:
                    sections.append((current_title, text))
            current_title = line[3:].strip()
            current = []
        else:
            current.append(line)
    if current:
        text = "\n".join(current).strip()
        if text:
            sections.append((current_title, text))
    return sections


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class Chunk:
    id: str
    card_id: str
    section: str
    text: str
    tokens: list[str]
    vector: list[float]
    title: str
    title_it: str
    domain: str
    status: str
    applies_to: list[str]
    sources: list[str]


class KnowledgeBase:
    def __init__(self, db: Database, knowledge_dir: Path = KNOWLEDGE_DIR):
        self.db = db
        self.dir = knowledge_dir
        self._chunks: list[Chunk] | None = None
        self._protocols: dict[str, dict[str, Any]] | None = None

    # ---------- indexing ----------
    def index(self) -> dict[str, Any]:
        cards_dir = self.dir / "cards"
        cards = sorted(cards_dir.glob("*.md"))
        indexed_cards = 0
        indexed_chunks = 0
        for path in cards:
            meta, body = parse_frontmatter(path)
            card_id = meta.get("id") or path.stem
            version = int(hashlib.sha256(path.read_bytes()).hexdigest()[:8], 16) % 100000
            self.db.execute(
                "INSERT OR REPLACE INTO kb_cards "
                "(id, title, domain, status, applies_to, sources, path, version, last_reviewed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    card_id,
                    meta.get("title", card_id),
                    meta.get("domain", "general"),
                    meta.get("status", "NEEDS_CLINICAL_REVIEW"),
                    dumps(meta.get("applies_to", [])),
                    dumps(meta.get("sources", [])),
                    str(path.relative_to(self.dir.parent)),
                    version,
                    meta.get("last_reviewed"),
                ),
            )
            self.db.execute("DELETE FROM kb_chunks WHERE card_id = ?", (card_id,))
            sections = split_sections(body)
            title = meta.get("title", card_id)
            title_it = meta.get("title_it", title)
            summary_it = meta.get("summary_it", "")
            for index, (section, text) in enumerate(sections):
                chunk_text = text
                if summary_it and index == 0:
                    chunk_text = text + "\n\nItalian summary: " + summary_it
                tokens = tokenize(f"{title} {title_it} {section} {chunk_text}")
                chunk_id = f"{card_id}:{index}"
                self.db.execute(
                    "INSERT INTO kb_chunks (id, card_id, section, text, tokens, vector, lang) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        chunk_id,
                        card_id,
                        section,
                        chunk_text,
                        dumps(tokens),
                        dumps(embed(tokens)),
                        "en",
                    ),
                )
                indexed_chunks += 1
            indexed_cards += 1
        self._chunks = None
        return {"cards": indexed_cards, "chunks": indexed_chunks}

    # ---------- retrieval ----------
    def chunks(self) -> list[Chunk]:
        if self._chunks is not None:
            return self._chunks
        rows = self.db.query(
            "SELECT c.*, k.title, k.domain, k.status, k.applies_to, k.sources, k.path "
            "FROM kb_chunks c JOIN kb_cards k ON k.id = c.card_id"
        )
        result: list[Chunk] = []
        title_it_map = {}
        for path in (self.dir / "cards").glob("*.md"):
            meta, _ = parse_frontmatter(path)
            if meta.get("id"):
                title_it_map[meta["id"]] = meta.get("title_it", meta.get("title", ""))
        for row in rows:
            result.append(
                Chunk(
                    id=row["id"],
                    card_id=row["card_id"],
                    section=row["section"],
                    text=row["text"],
                    tokens=loads(row["tokens"], []),
                    vector=loads(row["vector"], []),
                    title=row["title"],
                    title_it=title_it_map.get(row["card_id"], row["title"]),
                    domain=row["domain"],
                    status=row["status"],
                    applies_to=loads(row["applies_to"], []),
                    sources=loads(row["sources"], []),
                )
            )
        self._chunks = result
        return result

    def search(self, query: str, habitat: str | None = None, top_k: int = 6, min_score: float = 0.12) -> list[dict[str, Any]]:
        chunks = self.chunks()
        if not chunks or not query.strip():
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        query_vector = embed(query_tokens)
        query_terms = set(query_tokens)
        n_docs = len(chunks)
        df: dict[str, int] = {}
        for chunk in chunks:
            for term in set(chunk.tokens):
                df[term] = df.get(term, 0) + 1
        avg_len = mean(len(c.tokens) for c in chunks) or 1.0
        bm25: dict[str, float] = {}
        for chunk in chunks:
            score = 0.0
            counts: dict[str, int] = {}
            for token in chunk.tokens:
                counts[token] = counts.get(token, 0) + 1
            for term in query_terms:
                tf = counts.get(term, 0)
                if not tf:
                    continue
                idf = math.log((n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1)
                score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * len(chunk.tokens) / avg_len))
            bm25[chunk.id] = score
        max_bm25 = max(bm25.values()) or 1.0
        results: list[dict[str, Any]] = []
        for chunk in chunks:
            if habitat and chunk.applies_to and habitat not in chunk.applies_to:
                continue
            vector_score = max(0.0, cosine(query_vector, chunk.vector))
            keyword_score = bm25.get(chunk.id, 0.0) / max_bm25
            combined = 0.58 * keyword_score + 0.42 * vector_score
            if combined < min_score:
                continue
            results.append(
                {
                    "chunk_id": chunk.id,
                    "card_id": chunk.card_id,
                    "title": chunk.title,
                    "title_it": chunk.title_it,
                    "section": chunk.section,
                    "text": chunk.text,
                    "domain": chunk.domain,
                    "status": chunk.status,
                    "needs_review": chunk.status != "VALIDATED",
                    "applies_to": chunk.applies_to,
                    "sources": chunk.sources,
                    "score": round(combined, 3),
                    "vector_score": round(vector_score, 3),
                    "keyword_score": round(keyword_score, 3),
                }
            )
        results.sort(key=lambda item: item["score"], reverse=True)
        # Keep at most two chunks per card for diversity.
        selected: list[dict[str, Any]] = []
        counts: dict[str, int] = {}
        for item in results:
            if counts.get(item["card_id"], 0) >= 2:
                continue
            selected.append(item)
            counts[item["card_id"]] = counts.get(item["card_id"], 0) + 1
            if len(selected) >= top_k:
                break
        return selected

    def cards(self) -> list[dict[str, Any]]:
        rows = self.db.query("SELECT * FROM kb_cards ORDER BY domain, title")
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "domain": row["domain"],
                "status": row["status"],
                "applies_to": loads(row["applies_to"], []),
                "sources": loads(row["sources"], []),
                "version": row["version"],
                "path": row["path"],
            }
            for row in rows
        ]

    def card(self, card_id: str) -> dict[str, Any] | None:
        row = self.db.query_one("SELECT * FROM kb_cards WHERE id = ?", (card_id,))
        if not row:
            return None
        path = self.dir.parent / row["path"]
        meta: dict[str, Any] = {}
        body = ""
        if path.exists():
            meta, body = parse_frontmatter(path)
        return {
            "id": row["id"],
            "title": row["title"],
            "title_it": meta.get("title_it", row["title"]),
            "domain": row["domain"],
            "status": row["status"],
            "applies_to": loads(row["applies_to"], []),
            "sources": loads(row["sources"], []),
            "summary_it": meta.get("summary_it", ""),
            "body": body,
            "path": row["path"],
        }

    # ---------- protocols ----------
    def protocol(self, key: str | None) -> dict[str, Any] | None:
        if not key:
            return None
        if self._protocols is None:
            self._protocols = {}
            for path in (self.dir / "protocols").glob("*.md"):
                meta, body = parse_frontmatter(path)
                pid = meta.get("id", path.stem)
                key_name = path.stem
                self._protocols[key_name] = {**meta, "body": body, "file": str(path)}
                if pid:
                    self._protocols[pid] = self._protocols[key_name]
        return self._protocols.get(key)

    def protocol_step_texts(self, key: str | None, locale: str = "en") -> list[str]:
        protocol = self.protocol(key)
        if not protocol:
            return []
        return [step.get(locale) or step.get("en", "") for step in protocol.get("steps", [])]

    def all_protocols(self) -> list[dict[str, Any]]:
        self.protocol("chest_pain")
        seen = set()
        out = []
        for key, value in (self._protocols or {}).items():
            if value["id"] in seen:
                continue
            seen.add(value["id"])
            out.append(
                {
                    "id": value["id"],
                    "key": value.get("id", "").replace("protocol_", ""),
                    "title": value.get("title"),
                    "title_it": value.get("title_it"),
                    "severity": value.get("severity"),
                    "steps": value.get("steps", []),
                    "escalate_when_en": value.get("escalate_when_en", []),
                    "escalate_when_it": value.get("escalate_when_it", []),
                }
            )
        return out
