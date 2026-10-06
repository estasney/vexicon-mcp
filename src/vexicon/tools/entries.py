from typing import Annotated

from fastmcp.server.context import Context
from fastmcp.tools import ToolResult
from pydantic import Field

from vexicon.client import HybridClientProtocol
from vexicon.deps import GetClientDep
from vexicon.models.base import Filter, SpaceName
from vexicon.models.entries import Entry, NewEntry, UpdateEntriesInput
from vexicon.text_tools import plain_tool, records_tool

WhereField = Field(default=None, description="Metadata filter.")
WhereTextField = Field(default=None, description="Entry text filter.")


@plain_tool
async def add_entries(
    entries: list[NewEntry],
    space: SpaceName,
    ctx: Context,
    client: HybridClientProtocol = GetClientDep,
) -> ToolResult:
    """Store entries that follow the space readme."""
    await client.add_entries(space, entries)
    lines = [f"Stored {len(entries)} entries in {space!r}.", *(e.id for e in entries)]
    return ToolResult(content="\n".join(lines))


@records_tool
async def search(
    queries: list[str],
    space: SpaceName,
    ctx: Context,
    limit: Annotated[int, Field(description="Maximum entries returned.")] = 5,
    where: Filter | None = WhereField,
    where_text: Filter | None = WhereTextField,
    client: HybridClientProtocol = GetClientDep,
) -> list[Entry]:
    """Search a space and return one ranked list of entries for all queries."""
    return await client.search(
        space, queries, limit=limit, where=where, where_text=where_text
    )


@records_tool
async def list_entries(
    space: SpaceName,
    ctx: Context,
    ids: list[str] | None = None,
    where: Filter | None = WhereField,
    where_text: Filter | None = WhereTextField,
    limit: int | None = None,
    offset: int | None = None,
    client: HybridClientProtocol = GetClientDep,
) -> list[Entry]:
    """Fetch entries from a space."""
    return await client.list_entries(
        space,
        ids=ids,
        where=where,
        where_text=where_text,
        limit=limit,
        offset=offset,
    )


@plain_tool
async def update_entries(
    params: UpdateEntriesInput,
    ctx: Context,
    client: HybridClientProtocol = GetClientDep,
) -> ToolResult:
    """Update the text or metadata of entries by ID."""
    await client.update_entries(
        params.space, params.ids, texts=params.texts, metadata=params.metadata
    )
    return ToolResult(content=f"Updated {len(params.ids)} entries in {params.space!r}.")


@plain_tool
async def delete_entries(
    ids: list[str],
    space: SpaceName,
    ctx: Context,
    client: HybridClientProtocol = GetClientDep,
) -> ToolResult:
    """Delete entries by ID."""
    await client.delete_entries(space, ids)
    return ToolResult(content=f"Deleted {len(ids)} entries in {space!r}.")


ENTRY_TOOLS = [
    add_entries,
    search,
    list_entries,
    update_entries,
    delete_entries,
]
