import asyncio
from collections.abc import Coroutine
from pathlib import Path
from threading import Thread
from typing import Any, Self

from vexicon.client.async_client import AsyncHybridClient
from vexicon.embedding import Device
from vexicon.models.base import Filter, Metadata
from vexicon.models.entries import Entry, NewEntry
from vexicon.models.spaces import SpaceDescription, SpaceInfo, SpaceSummary


class HybridClient:
    """Enter with `with` before use; entering migrates the keyword index and rebuilds it from Chroma."""

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
        self.inner = AsyncHybridClient(
            persistent_path,
            index_db_path,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            rrf_rank_offset=rrf_rank_offset,
            device=device,
            idle_seconds=idle_seconds,
        )
        self.loop = asyncio.new_event_loop()
        self.thread = Thread(target=self.loop.run_forever, daemon=True)

    def run[T](self, coroutine: Coroutine[Any, Any, T]) -> T:
        if not self.thread.is_alive():
            coroutine.close()
            raise RuntimeError("Enter the client with `with` before calling it")
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result()

    def __enter__(self) -> Self:
        self.thread.start()
        self.run(self.inner.__aenter__())
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            self.run(self.inner.__aexit__(*exc))
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join()
            self.loop.close()

    def list_spaces(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[SpaceSummary]:
        return self.run(self.inner.list_spaces(limit, offset))

    def create_space(
        self,
        name: str,
        readme: str | None = None,
        embedding_repo_id: str | None = None,
        metadata: Metadata | None = None,
    ) -> SpaceSummary:
        return self.run(
            self.inner.create_space(name, readme, embedding_repo_id, metadata)
        )

    def get_space(self, name: str) -> SpaceInfo:
        return self.run(self.inner.get_space(name))

    def describe_space(self, name: str, sample_size: int = 5) -> SpaceDescription:
        return self.run(self.inner.describe_space(name, sample_size))

    def update_space(
        self,
        name: str,
        new_name: str | None = None,
        readme: str | None = None,
        metadata: Metadata | None = None,
    ) -> None:
        return self.run(self.inner.update_space(name, new_name, readme, metadata))

    def delete_space(self, name: str) -> None:
        return self.run(self.inner.delete_space(name))

    def add_entries(self, space: str, entries: list[NewEntry]) -> None:
        return self.run(self.inner.add_entries(space, entries))

    def update_entries(
        self,
        space: str,
        ids: list[str],
        texts: list[str] | None = None,
        metadata: list[Metadata] | None = None,
    ) -> None:
        return self.run(self.inner.update_entries(space, ids, texts, metadata))

    def delete_entries(self, space: str, ids: list[str]) -> None:
        return self.run(self.inner.delete_entries(space, ids))

    def list_entries(
        self,
        space: str,
        ids: list[str] | None = None,
        where: Filter | None = None,
        where_text: Filter | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Entry]:
        return self.run(
            self.inner.list_entries(space, ids, where, where_text, limit, offset)
        )

    def search(
        self,
        space: str,
        queries: list[str],
        limit: int = 10,
        where: Filter | None = None,
        where_text: Filter | None = None,
    ) -> list[Entry]:
        return self.run(self.inner.search(space, queries, limit, where, where_text))

    def sync(self) -> None:
        return self.run(self.inner.sync())
