from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings


class RetrievalError(RuntimeError):
    """Raised when guideline retrieval cannot complete."""


@dataclass(frozen=True)
class RetrievedGuideline:
    content: str
    source: str
    page_number: int | str | None

    @property
    def citation(self) -> str:
        source_name = Path(self.source).name if self.source else "Unknown source"
        if self.page_number is None:
            return source_name
        return f"{source_name} p.{self.page_number}"


def get_guideline_collection(
    chroma_path: str | None = None,
    collection_name: str | None = None,
) -> Any:
    settings = get_settings()
    resolved_path = chroma_path or settings.chroma_path
    resolved_collection = collection_name or settings.chroma_collection

    try:
        import chromadb

        client = chromadb.PersistentClient(path=resolved_path)
        return client.get_collection(name=resolved_collection)
    except Exception as exc:
        raise RetrievalError(
            f"Unable to load Chroma collection '{resolved_collection}' at '{resolved_path}'."
        ) from exc


def retrieve_relevant_guidelines(
    query: str,
    top_k: int | None = None,
    collection: Any | None = None,
) -> list[RetrievedGuideline]:
    settings = get_settings()
    resolved_top_k = top_k or settings.retrieval_top_k
    resolved_collection = collection or get_guideline_collection()

    try:
        results = resolved_collection.query(
            query_texts=[query],
            include=["documents", "metadatas"],
            n_results=resolved_top_k,
        )
    except Exception as exc:
        raise RetrievalError("Unable to query Chroma guideline collection.") from exc

    documents = _first_result_list(results, "documents")
    metadatas = _first_result_list(results, "metadatas")

    guidelines: list[RetrievedGuideline] = []
    for index, document in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) else {}
        metadata = metadata or {}
        guidelines.append(
            RetrievedGuideline(
                content=str(document),
                source=str(metadata.get("source", "Unknown source")),
                page_number=metadata.get("page_number"),
            )
        )

    if not guidelines:
        raise RetrievalError("Chroma returned no relevant guideline chunks.")

    return guidelines


def _first_result_list(results: dict[str, Any], key: str) -> list[Any]:
    values = results.get(key) or []
    if not values:
        return []
    first = values[0]
    return first if isinstance(first, list) else []
