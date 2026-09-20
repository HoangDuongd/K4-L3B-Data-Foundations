from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]
        chunks: list[str] = []
        for start in range(0, len(sentences), self.max_sentences_per_chunk):
            chunks.append(" ".join(sentences[start : start + self.max_sentences_per_chunk]).strip())
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text.strip(), self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        current_text = current_text.strip()
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text]

        if not remaining_separators:
            return [
                current_text[start : start + self.chunk_size].strip()
                for start in range(0, len(current_text), self.chunk_size)
                if current_text[start : start + self.chunk_size].strip()
            ]

        separator = remaining_separators[0]
        next_separators = remaining_separators[1:]
        if separator == "":
            raw_parts = [
                current_text[start : start + self.chunk_size]
                for start in range(0, len(current_text), self.chunk_size)
            ]
        else:
            raw_parts = current_text.split(separator)

        split_parts: list[str] = []
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            if len(part) > self.chunk_size:
                split_parts.extend(self._split(part, next_separators))
            else:
                split_parts.append(part)

        return self._merge_parts(split_parts, separator)

    def _merge_parts(self, parts: list[str], separator: str) -> list[str]:
        chunks: list[str] = []
        current = ""
        joiner = separator if separator else ""

        for part in parts:
            candidate = part if not current else f"{current}{joiner}{part}"
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue

            if current:
                chunks.append(current.strip())
            current = part

        if current:
            chunks.append(current.strip())
        return chunks


class PolicyStructureChunker:
    """Chunk crawled policy documents while retaining document context.

    The sentence pass keeps prose coherent. Crawled tables that look like one
    very long sentence are then bounded by the recursive pass. The document
    title is repeated so table fragments still carry their subject.
    """

    def __init__(self, chunk_size: int = 450, max_sentences: int = 2) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.chunk_size = chunk_size
        self.max_sentences = max(1, max_sentences)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        text = text.replace("\u00a0", " ").strip()
        title = self._find_title(text)
        prefix = f"Tài liệu: {title}\n\n" if title else ""
        available = max(100, self.chunk_size - len(prefix))
        chunks: list[str] = []
        sentence_chunks = SentenceChunker(self.max_sentences).chunk(text)
        for sentence_chunk in sentence_chunks:
            pieces = RecursiveChunker(chunk_size=available).chunk(sentence_chunk)
            for piece in pieces:
                chunks.append(f"{prefix}{piece}".strip())
        return chunks

    def _find_title(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:12]:
            if "| Shopee Trung tâm trợ giúp" in line:
                return line.split("|", 1)[0].strip()
        for line in lines:
            candidate = line.lstrip("# ").strip()
            if candidate and not candidate.lower().startswith("shopee article"):
                return candidate[:180]
        return ""


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    norm_a = math.sqrt(_dot(vec_a, vec_a))
    norm_b = math.sqrt(_dot(vec_b, vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=0),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }

        comparison = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            count = len(chunks)
            avg_length = sum(len(chunk) for chunk in chunks) / count if count else 0
            comparison[name] = {
                "count": count,
                "avg_length": avg_length,
                "chunks": chunks,
            }
        return comparison
