from fastmcp import FastMCP

from vexicon.client import AsyncHybridClient
from vexicon.deps import hybrid_client_lifespan
from vexicon.resources import SpacesProvider
from vexicon.settings import Settings, get_settings
from vexicon.tools import TOOLS


def build_server(settings: Settings) -> FastMCP:
    client = AsyncHybridClient(
        settings.persistent_path,
        settings.index_db_path,
        vector_weight=settings.vector_weight,
        keyword_weight=settings.keyword_weight,
        rrf_rank_offset=settings.rrf_rank_offset,
        device=settings.device,
        idle_seconds=settings.idle_seconds,
    )
    mcp = FastMCP(
        "vexicon",
        instructions="A general knowledge store that saves notes and reference "
        "material in named spaces for later search.",
        lifespan=hybrid_client_lifespan(client),
    )
    for tool in TOOLS:
        mcp.add_tool(tool.model_copy(update={"tags": {"vexicon"}}))
    mcp.add_provider(SpacesProvider(client))
    return mcp


def main() -> None:
    """Entry point for the vexicon script, which serves over stdio only."""
    build_server(get_settings()).run(transport="stdio")
