
"""Deterministic chunking strategies for the Practo knowledge base."""

from dataclasses import dataclass
import re

from src.practo_agent.rag.document_loader import KnowledgeDocument


@dataclass(frozen=True)
class TextChunk:
    """A chunk with source metadata for retrieval and evaluation."""

    chunk_id: str
    source_id: str
    source_path: str
    title: str
    topic: str
    strategy: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int


def fixed_size_chunk(
    document: KnowledgeDocument,
    chunk_size: int = 400,
    overlap: int = 80,
) -> list[TextChunk]:
    """Split a document into fixed character windows with overlap.

    Offsets refer to the original document text. Text is not stripped,
    so the relationship between offsets and source text remains exact.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0:
        raise ValueError("overlap cannot be negative.")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    chunks = []
    start = 0
    chunk_index = 0
    text_length = len(document.text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk_text = document.text[start:end]

        chunks.append(
            TextChunk(
                chunk_id=(
                    f"{document.source_id}::fixed::{chunk_index:04d}"
                ),
                source_id=document.source_id,
                source_path=document.source_path,
                title=document.title,
                topic=document.topic,
                strategy="fixed_size",
                chunk_index=chunk_index,
                text=chunk_text,
                start_char=start,
                end_char=end,
            )
        )

        if end == text_length:
            break

        start = end - overlap
        chunk_index += 1

    return chunks


def split_sentences(text: str) -> list[str]:
    """Split text at sentence-ending punctuation followed by whitespace.

    This lightweight splitter is suitable for the authored capstone
    documents. It is not a full linguistic sentence parser.
    """

    # Markdown headings are represented separately in chunk metadata.
    body_lines = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
    ]
    body = "\n".join(body_lines).strip()

    if not body:
        return []

    pieces = re.split(r"(?<=[.!?])\s+", body)

    return [
        piece.strip()
        for piece in pieces
        if piece.strip()
    ]


def sentence_based_chunk(
    document: KnowledgeDocument,
    sentences_per_chunk: int = 3,
    overlap_sentences: int = 1,
) -> list[TextChunk]:
    """Group sentences into chunks with optional sentence overlap."""

    if sentences_per_chunk <= 0:
        raise ValueError(
            "sentences_per_chunk must be greater than zero."
        )

    if overlap_sentences < 0:
        raise ValueError("overlap_sentences cannot be negative.")

    if overlap_sentences >= sentences_per_chunk:
        raise ValueError(
            "overlap_sentences must be smaller than sentences_per_chunk."
        )

    sentences = split_sentences(document.text)
    chunks = []

    start_index = 0
    chunk_index = 0

    while start_index < len(sentences):
        end_index = min(
            start_index + sentences_per_chunk,
            len(sentences),
        )

        selected_sentences = sentences[start_index:end_index]
        chunk_text = " ".join(selected_sentences)

        chunks.append(
            TextChunk(
                chunk_id=(
                    f"{document.source_id}::sentence::{chunk_index:04d}"
                ),
                source_id=document.source_id,
                source_path=document.source_path,
                title=document.title,
                topic=document.topic,
                strategy="sentence",
                chunk_index=chunk_index,
                text=chunk_text,
                # Sentence chunks are reconstructed from complete
                # sentences, so these are sentence-index offsets,
                # not character offsets in the original Markdown.
                start_char=start_index,
                end_char=end_index,
            )
        )

        if end_index == len(sentences):
            break

        start_index = end_index - overlap_sentences
        chunk_index += 1

    return chunks
