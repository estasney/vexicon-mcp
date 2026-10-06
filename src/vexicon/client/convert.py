from typing import cast

from chromadb import Collection
from chromadb.api.types import GetResult

from vexicon.models.base import Metadata
from vexicon.models.entries import Entry
from vexicon.models.spaces import SpaceSummary
from vexicon.queries.fusion import Hit


def entries_from(result: GetResult) -> list[Entry]:
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    return [
        Entry(
            id=entry_id,
            text=documents[index] if index < len(documents) else None,
            metadata_raw=cast("Metadata | None", metadatas[index])
            if index < len(metadatas)
            else None,
        )
        for index, entry_id in enumerate(result["ids"])
    ]


def entry_from(hit: Hit) -> Entry:
    return Entry(id=hit.chroma_id, text=hit.document, metadata_raw=hit.metadata)


def space_summary_from(collection: Collection) -> SpaceSummary:
    return SpaceSummary(
        name=collection.name,
        metadata_raw=cast("Metadata | None", collection.metadata),
    )
