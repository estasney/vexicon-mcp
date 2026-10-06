from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager

from fastmcp.dependencies import Depends
from fastmcp.server.dependencies import get_context
from fastmcp.server.lifespan import Lifespan, lifespan

from vexicon.client import AsyncHybridClient, HybridClientProtocol


def hybrid_client_lifespan(client: AsyncHybridClient) -> Lifespan:
    @lifespan
    async def run(server: object) -> AsyncGenerator[dict[str, object]]:
        async with client:
            yield {"hybrid_client": client}

    return run


def get_hybrid_client() -> HybridClientProtocol:
    return get_context().lifespan_context["hybrid_client"]


@contextmanager
def borrow_hybrid_client() -> Generator[HybridClientProtocol]:
    """Provides the server's hybrid client to a tool without closing it when the call ends."""
    yield get_hybrid_client()


GetClientDep = Depends(borrow_hybrid_client)
