from typing import Protocol

from vexicon.models.base import Filter, Metadata
from vexicon.models.entries import Entry, NewEntry
from vexicon.models.spaces import SpaceDescription, SpaceInfo, SpaceSummary


class HybridClientProtocol(Protocol):
    async def list_spaces(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[SpaceSummary]: ...

    async def create_space(
        self,
        name: str,
        readme: str | None = None,
        embedding_repo_id: str | None = None,
        metadata: Metadata | None = None,
    ) -> SpaceSummary: ...

    async def get_space(self, name: str) -> SpaceInfo: ...

    async def describe_space(
        self, name: str, sample_size: int = 5
    ) -> SpaceDescription: ...

    async def update_space(
        self,
        name: str,
        new_name: str | None = None,
        readme: str | None = None,
        metadata: Metadata | None = None,
    ) -> None: ...

    async def delete_space(self, name: str) -> None: ...

    async def add_entries(self, space: str, entries: list[NewEntry]) -> None: ...

    async def update_entries(
        self,
        space: str,
        ids: list[str],
        texts: list[str] | None = None,
        metadata: list[Metadata] | None = None,
    ) -> None: ...

    async def delete_entries(self, space: str, ids: list[str]) -> None: ...

    async def list_entries(
        self,
        space: str,
        ids: list[str] | None = None,
        where: Filter | None = None,
        where_text: Filter | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Entry]: ...

    async def search(
        self,
        space: str,
        queries: list[str],
        limit: int = 10,
        where: Filter | None = None,
        where_text: Filter | None = None,
    ) -> list[Entry]: ...

    async def sync(self) -> None: ...
