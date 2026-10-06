from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from chromadb.api.types import QueryResult

from vexicon.models.base import Metadata
from vexicon.queries.selects import KeywordRow


@dataclass(frozen=True)
class Hit:
    chroma_id: str
    document: str
    metadata: Metadata | None


def group_by_phrase(rows: Sequence[KeywordRow], phrase_count: int) -> list[list[Hit]]:
    grouped: list[list[Hit]] = [[] for _ in range(phrase_count)]
    for phrase_index, chroma_id, document, metadata, _ in rows:
        grouped[phrase_index].append(
            Hit(chroma_id=chroma_id, document=document, metadata=metadata)
        )
    return grouped


def vector_hits(result: QueryResult) -> list[list[Hit]]:
    """One list of hits per query text, in Chroma's rank order."""
    documents = result["documents"]
    metadatas = result["metadatas"]
    if documents is None or metadatas is None:
        raise ValueError("Chroma result lacks documents or metadatas")
    return [
        [
            Hit(
                chroma_id=chroma_id,
                document=document,
                metadata=cast("Metadata | None", metadata),
            )
            for chroma_id, document, metadata in zip(
                ids, query_documents, query_metadatas, strict=True
            )
        ]
        for ids, query_documents, query_metadatas in zip(
            result["ids"], documents, metadatas, strict=True
        )
    ]


@dataclass(frozen=True)
class Ranking:
    hits: Sequence[Hit]
    weight: float


def fuse(rankings: Sequence[Ranking], rank_offset: int) -> list[Hit]:
    """Weighted reciprocal rank fusion keyed by chroma_id. Each id keeps its first hit, and ties keep first appearance."""
    scores: defaultdict[str, float] = defaultdict(float)
    first_hits: dict[str, Hit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking.hits, start=1):
            scores[hit.chroma_id] += ranking.weight / (rank_offset + rank)
            first_hits.setdefault(hit.chroma_id, hit)
    return sorted(first_hits.values(), key=lambda hit: -scores[hit.chroma_id])
