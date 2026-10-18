
"""Load project-authored knowledge-base documents with source metadata."""

from dataclasses import dataclass
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_KB_DIR = PROJECT_ROOT / "data" / "knowledge_base"


@dataclass(frozen=True)
class KnowledgeDocument:
    """A source document before chunking."""

    source_id: str
    source_path: str
    title: str
    topic: str
    text: str


def _extract_title(text: str, fallback: str) -> str:
    """Extract the first Markdown H1 title or use a readable fallback."""

    for line in text.splitlines():
        match = re.match(r"^\s*#\s+(.+?)\s*#*\s*$", line)
        if match:
            return match.group(1).strip()

    return fallback.replace("_", " ").replace("-", " ").title()


def load_knowledge_documents(
    kb_dir: Path = DEFAULT_KB_DIR,
) -> list[KnowledgeDocument]:
    """Load all Markdown files in deterministic filename order.

    Raises:
        FileNotFoundError: if the knowledge-base directory is missing.
        ValueError: if no Markdown files exist or a file is empty.
    """

    if not kb_dir.is_dir():
        raise FileNotFoundError(
            f"Knowledge-base directory does not exist: {kb_dir}"
        )

    paths = sorted(
        (path for path in kb_dir.glob("*.md") if path.is_file()),
        key=lambda path: path.name.lower(),
    )

    if not paths:
        raise ValueError(
            f"No Markdown documents found in {kb_dir}."
        )

    documents = []

    for path in paths:
        text = path.read_text(encoding="utf-8").strip()

        if not text:
            raise ValueError(
                f"Knowledge-base document is empty: {path.name}"
            )

        source_id = path.stem
        title = _extract_title(text, source_id)

        documents.append(
            KnowledgeDocument(
                source_id=source_id,
                source_path=path.resolve().relative_to(PROJECT_ROOT).as_posix(),
                title=title,
                topic=source_id,
                text=text,
            )
        )

    source_ids = [document.source_id for document in documents]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Knowledge-base source IDs must be unique.")

    return documents
