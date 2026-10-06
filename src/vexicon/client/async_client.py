import asyncio
from pathlib import Path
from typing import Self, cast

import chromadb
from chromadb import Collection
from chromadb.api import ClientAPI
from chromadb.api.types import (
    Embeddable,
    EmbeddingFunction,
    GetResult,
    Metadatas,
    QueryResult,
    Where,
    WhereDocument,
)
from chromadb.config import Settings as ChromaDbSettings
from sqlalchemy import bindparam, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from vexicon import orm
from vexicon.client.convert import entries_from, entry_from, space_summary_from
from vexicon.client.errors import (
    DuplicateEntryIdsError,
    EntriesExistError,
    SpaceNotIndexedError,
)
from vexicon.db import create_index_engine, run_migrations
from vexicon.embedding import (
    Device,
    release_embedding_models,
    resolve_embedding_function,
)
from vexicon.idle_proxy import IdleUnloadingProxy
from vexicon.models.base import Filter, Metadata
from vexicon.models.entries import Entry, NewEntry
from vexicon.models.spaces import SpaceDescription, SpaceInfo, SpaceSummary
from vexicon.queries.fusion import (
    Hit,
    Ranking,
    fuse,
    group_by_phrase,
    vector_hits,
)
from vexicon.queries.matching import match_expression
from vexicon.queries.selects import collection_id_select, keyword_search_select


def space_metadata(
    metadata: Metadata | None,
    readme: str | None,
    repo_id: str | None,
    max_tokens: int | None,
) -> Metadata | None:
    own: Metadata = {
        "readme": readme,
        "embedding_repo_id": repo_id,
        "embedding_max_tokens": max_tokens,
    }
    merged = {
        **(metadata or {}),
        **{key: value for key, value in own.items() if value is not None},
    }
    return merged or None


def close_chroma_client(client: ClientAPI) -> None:
    client.close()  # pyright: ignore[reportAttributeAccessIssue] # Technically not on ClientAPI


def records_from(result: GetResult) -> list[tuple[str, str, Metadata | None]]:
    documents = result["documents"]
    metadatas = result["metadatas"]
    if documents is None or metadatas is None:
        raise RuntimeError("Chroma result lacks documents or metadatas")
    return [
        (chroma_id, document, cast("Metadata | None", metadata))
        for chroma_id, document, metadata in zip(
            result["ids"], documents, metadatas, strict=True
        )
    ]


def rows_from(collection_id: int, result: GetResult) -> list[dict[str, object]]:
    return [
        {
            "collection_id": collection_id,
            "chroma_id": chroma_id,
            "document": document,
            "metadata": metadata,
        }
        for chroma_id, document, metadata in records_from(result)
    ]


class AsyncHybridClient:
    """Enter with `async with` before use; entering migrates the keyword index and rebuilds it from Chroma."""

    def __init__(
        self,
        persistent_path: Path,
        index_db_path: Path,
        *,
        vector_weight: float = 1.0,
        keyword_weight: float = 1.0,
        rrf_rank_offset: int = 60,
        device: Device = Device.auto,
        idle_seconds: float = 300.0,
    ) -> None:
        self.index_db_path = index_db_path
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.rrf_rank_offset = rrf_rank_offset
        self.device = device
        self.chroma = IdleUnloadingProxy(
            load=lambda: chromadb.PersistentClient(
                path=str(persistent_path),
                settings=ChromaDbSettings(anonymized_telemetry=False),
            ),
            idle_seconds=idle_seconds,
            unload=close_chroma_client,
            reclaim=release_embedding_models,
        )
        self.sql_engine = create_index_engine(index_db_path)

    async def __aenter__(self) -> Self:
        await asyncio.to_thread(run_migrations, self.index_db_path)
        await self.sync()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.chroma.aclose()
        await self.sql_engine.dispose()

    async def list_spaces(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[SpaceSummary]:
        async def list_chroma() -> list[Collection]:
            async with self.chroma.lease() as client:
                return list(await asyncio.to_thread(client.list_collections))

        async def list_sql() -> set[str]:
            async with self.sql_engine.connect() as connection:
                names = await connection.execute(select(orm.Collection.name))
                return set(names.scalars().all())

        collections, indexed = await asyncio.gather(list_chroma(), list_sql())
        matched = [col for col in collections if col.name in indexed]
        start = offset or 0
        end = None if limit is None else start + limit
        return [space_summary_from(col) for col in matched[start:end]]

    async def create_space(
        self,
        name: str,
        readme: str | None = None,
        embedding_repo_id: str | None = None,
        metadata: Metadata | None = None,
    ) -> SpaceSummary:
        def write_chroma(client: ClientAPI) -> Collection:
            embedding_function, max_tokens = resolve_embedding_function(
                embedding_repo_id, self.device
            )
            return client.create_collection(
                name=name,
                embedding_function=cast(
                    "EmbeddingFunction[Embeddable]", embedding_function
                ),
                metadata=space_metadata(
                    metadata, readme, embedding_repo_id, max_tokens
                ),
            )

        async with self.chroma.lease() as client:
            collection = await asyncio.to_thread(write_chroma, client)
        async with self.sql_engine.begin() as connection:
            await connection.execute(
                insert(orm.Collection).values(name=collection.name)
            )
        return space_summary_from(collection)

    async def get_space(self, name: str) -> SpaceInfo:
        def read_chroma(client: ClientAPI) -> tuple[Collection, int]:
            collection = client.get_collection(name=name)
            return collection, collection.count()

        async with self.chroma.lease() as client:
            collection, count = await asyncio.to_thread(read_chroma, client)
        return SpaceInfo(
            name=collection.name,
            metadata_raw=cast("Metadata | None", collection.metadata),
            id=str(collection.id),
            count=count,
        )

    async def describe_space(self, name: str, sample_size: int = 5) -> SpaceDescription:
        def read_chroma(client: ClientAPI) -> tuple[Collection, int, GetResult]:
            collection = client.get_collection(name=name)
            return collection, collection.count(), collection.peek(limit=sample_size)

        async with self.chroma.lease() as client:
            collection, count, sample = await asyncio.to_thread(read_chroma, client)
        return SpaceDescription(
            name=collection.name,
            metadata_raw=cast("Metadata | None", collection.metadata),
            id=str(collection.id),
            count=count,
            sample=entries_from(sample),
        )

    async def update_space(
        self,
        name: str,
        new_name: str | None = None,
        readme: str | None = None,
        metadata: Metadata | None = None,
    ) -> None:
        """A None value in metadata removes that key."""
        changes = dict(metadata or {})
        if readme is not None:
            changes["readme"] = readme

        def write_chroma(client: ClientAPI) -> None:
            collection = client.get_collection(name=name)
            merged = None
            if changes:
                combined = {**(collection.metadata or {}), **changes}
                merged = {
                    key: value for key, value in combined.items() if value is not None
                }
            collection.modify(name=new_name, metadata=merged)

        async with self.chroma.lease() as client:
            await asyncio.to_thread(write_chroma, client)
        if new_name is None:
            return
        async with self.sql_engine.begin() as connection:
            await connection.execute(
                update(orm.Collection)
                .where(orm.Collection.name == name)
                .values(name=new_name)
            )

    async def delete_space(self, name: str) -> None:
        def write_chroma(client: ClientAPI) -> None:
            client.delete_collection(name=name)

        async with self.chroma.lease() as client:
            await asyncio.to_thread(write_chroma, client)
        async with self.sql_engine.begin() as connection:
            await connection.execute(
                delete(orm.Collection).where(orm.Collection.name == name)
            )

    async def add_entries(self, space: str, entries: list[NewEntry]) -> None:
        ids = [entry.id for entry in entries]
        if len(set(ids)) != len(ids):
            raise DuplicateEntryIdsError
        documents = [entry.text for entry in entries]
        metadatas: list[Metadata] = [
            {**(entry.meta or {}), "created_at": entry.created_at} for entry in entries
        ]

        def write_chroma(client: ClientAPI) -> GetResult:
            collection = client.get_collection(name=space)
            existing = collection.get(ids=ids, include=[])["ids"]
            if existing:
                raise EntriesExistError(space, existing)
            collection.add(
                ids=ids, documents=documents, metadatas=cast("Metadatas", metadatas)
            )
            return collection.get(ids=ids, include=["documents", "metadatas"])

        async with self.sql_engine.connect() as connection:
            collection_id = await connection.scalar(collection_id_select(space))
            if collection_id is None:
                raise SpaceNotIndexedError(space)
        async with self.chroma.lease() as client:
            written = await asyncio.to_thread(write_chroma, client)
        async with self.sql_engine.begin() as connection:
            await connection.execute(
                insert(orm.Document), rows_from(collection_id, written)
            )

    async def update_entries(
        self,
        space: str,
        ids: list[str],
        texts: list[str] | None = None,
        metadata: list[Metadata] | None = None,
    ) -> None:
        def write_chroma(client: ClientAPI) -> GetResult:
            collection = client.get_collection(name=space)
            collection.update(
                ids=ids,
                metadatas=cast("Metadatas | None", metadata),
                documents=texts,
            )
            return collection.get(ids=ids, include=["documents", "metadatas"])

        async def write_sql(connection: AsyncConnection, current: GetResult) -> None:
            statement = (
                update(orm.Document)
                .where(
                    orm.Document.collection_id
                    == collection_id_select(space).scalar_subquery(),
                    orm.Document.chroma_id == bindparam("key"),
                )
                .values(document=bindparam("text"), meta=bindparam("fields"))
            )
            rows = [
                {"key": chroma_id, "text": document, "fields": metadata}
                for chroma_id, document, metadata in records_from(current)
            ]
            await connection.execute(statement, rows)

        async with self.chroma.lease() as client:
            current = await asyncio.to_thread(write_chroma, client)
        async with self.sql_engine.begin() as connection:
            await write_sql(connection, current)

    async def delete_entries(self, space: str, ids: list[str]) -> None:
        def write_chroma(client: ClientAPI) -> None:
            client.get_collection(name=space).delete(ids=ids)

        async with self.chroma.lease() as client:
            await asyncio.to_thread(write_chroma, client)
        async with self.sql_engine.begin() as connection:
            await connection.execute(
                delete(orm.Document).where(
                    orm.Document.collection_id
                    == collection_id_select(space).scalar_subquery(),
                    orm.Document.chroma_id.in_(ids),
                )
            )

    async def list_entries(
        self,
        space: str,
        ids: list[str] | None = None,
        where: Filter | None = None,
        where_text: Filter | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Entry]:
        def read_chroma(client: ClientAPI) -> GetResult:
            return client.get_collection(name=space).get(
                ids=ids,
                where=cast("Where | None", where),
                where_document=cast("WhereDocument | None", where_text),
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"],
            )

        async with self.chroma.lease() as client:
            return entries_from(await asyncio.to_thread(read_chroma, client))

    async def search(
        self,
        space: str,
        queries: list[str],
        limit: int = 10,
        where: Filter | None = None,
        where_text: Filter | None = None,
    ) -> list[Entry]:
        """Fuses every query's vector and keyword rankings into one list."""

        def query_chroma(client: ClientAPI) -> QueryResult:
            return client.get_collection(name=space).query(
                query_texts=queries,
                n_results=limit,
                where=cast("Where | None", where),
                where_document=cast("WhereDocument | None", where_text),
                include=["documents", "metadatas"],
            )

        async def query_vector() -> list[list[Hit]]:
            async with self.chroma.lease() as client:
                result = await asyncio.to_thread(query_chroma, client)
            return vector_hits(result)

        async def query_sql(collection_id: int) -> list[list[Hit]]:
            expressions = [
                (index, expression)
                for index, phrase in enumerate(queries)
                if (expression := match_expression(phrase)) is not None
            ]
            if not expressions:
                return group_by_phrase([], len(queries))
            async with self.sql_engine.connect() as connection:
                result = await connection.execute(
                    keyword_search_select(
                        collection_id, expressions, limit, where, where_text
                    )
                )
                return group_by_phrase(result.tuples().all(), len(queries))

        async with self.sql_engine.connect() as connection:
            collection_id = await connection.scalar(collection_id_select(space))
        if collection_id is None:
            raise SpaceNotIndexedError(space)
        vector, keyword = await asyncio.gather(query_vector(), query_sql(collection_id))
        rankings = [
            *(Ranking(hits, self.vector_weight) for hits in vector),
            *(Ranking(hits, self.keyword_weight) for hits in keyword),
        ]
        return [entry_from(hit) for hit in fuse(rankings, self.rrf_rank_offset)[:limit]]

    async def sync(self) -> None:
        """Rebuilds the keyword index from every Chroma collection."""

        def read_chroma(client: ClientAPI) -> list[tuple[str, GetResult]]:
            return [
                (col.name, col.get(include=["documents", "metadatas"]))
                for col in client.list_collections()
            ]

        async def write_sql(
            connection: AsyncConnection, snapshot: list[tuple[str, GetResult]]
        ) -> None:
            await connection.execute(delete(orm.Document))
            await connection.execute(delete(orm.Collection))
            for name, result in snapshot:
                collection_id = await connection.scalar(
                    insert(orm.Collection)
                    .values(name=name)
                    .returning(orm.Collection.id)
                )
                if collection_id is None:
                    raise RuntimeError("Collection insert returned no id")
                rows = rows_from(collection_id, result)
                if rows:
                    await connection.execute(insert(orm.Document), rows)

        async with self.chroma.lease() as client:
            snapshot = await asyncio.to_thread(read_chroma, client)
        async with self.sql_engine.begin() as connection:
            await write_sql(connection, snapshot)
