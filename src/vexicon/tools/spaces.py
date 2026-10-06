from typing import Annotated

from fastmcp.server.context import Context
from fastmcp.tools import ToolResult
from pydantic import Field

from vexicon.client import HybridClientProtocol
from vexicon.deps import GetClientDep
from vexicon.models.base import Readme, SpaceName
from vexicon.models.embeddings import EmbeddingRepoId
from vexicon.models.spaces import SpaceDescription, SpaceMetadata, SpaceSummary
from vexicon.text_tools import plain_tool, record_tool, table_tool


@table_tool
async def list_spaces(
    ctx: Context,
    limit: int | None = None,
    offset: int | None = None,
    client: HybridClientProtocol = GetClientDep,
) -> list[SpaceSummary]:
    """List spaces with their readme and embedding model."""
    return await client.list_spaces(limit=limit, offset=offset)


@plain_tool
async def create_space(
    space: SpaceName,
    ctx: Context,
    readme: Readme | None = None,
    embedding_repo_id: EmbeddingRepoId | None = None,
    metadata: Annotated[
        SpaceMetadata | None, Field(description="Other space metadata.")
    ] = None,
    batch_size: Annotated[
        int, Field(ge=1, description="Embedding model batch size.")
    ] = 32,
    client: HybridClientProtocol = GetClientDep,
) -> ToolResult:
    """Create a space."""
    await client.create_space(
        space,
        readme=readme,
        embedding_repo_id=embedding_repo_id,
        metadata=metadata,
        batch_size=batch_size,
    )
    await ctx.session.send_resource_list_changed()
    return ToolResult(content=f"Created space {space!r}.")


@record_tool
async def describe_space(
    space: SpaceName,
    ctx: Context,
    sample_size: int = 5,
    client: HybridClientProtocol = GetClientDep,
) -> SpaceDescription:
    """Show a space with its entry count and first entries."""
    return await client.describe_space(space, sample_size=sample_size)


@plain_tool
async def update_space(
    space: SpaceName,
    ctx: Context,
    new_name: SpaceName | None = None,
    readme: Readme | None = None,
    metadata: Annotated[
        SpaceMetadata | None,
        Field(description="Keys to add or change where a null value removes the key."),
    ] = None,
    client: HybridClientProtocol = GetClientDep,
) -> ToolResult:
    """Rename a space or change its readme and metadata."""
    await client.update_space(
        space, new_name=new_name, readme=readme, metadata=metadata
    )
    if new_name is not None:
        await ctx.session.send_resource_list_changed()
    return ToolResult(content=f"Updated space {(new_name or space)!r}.")


@plain_tool
async def delete_space(
    space: SpaceName,
    ctx: Context,
    client: HybridClientProtocol = GetClientDep,
) -> ToolResult:
    """Delete a space and every entry in it."""
    await client.delete_space(space)
    await ctx.session.send_resource_list_changed()
    return ToolResult(content=f"Deleted space {space!r}.")


SPACE_TOOLS = [
    list_spaces,
    create_space,
    describe_space,
    update_space,
    delete_space,
]
