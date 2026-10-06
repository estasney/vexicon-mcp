from collections.abc import Sequence

from fastmcp.resources import FunctionResource, Resource
from fastmcp.server.providers import Provider

from vexicon.client import HybridClientProtocol


def space_uri(name: str) -> str:
    return f"vexicon://space/{name}"


class SpacesProvider(Provider):
    """Publishes every live space as a readable resource.

    `resources/list` reflects the current set of spaces. Tools that add,
    rename, or remove a space must call `ctx.session.send_resource_list_changed`.
    Reading a space resource returns its name, id, metadata, and count.
    """

    def __init__(self, client: HybridClientProtocol) -> None:
        super().__init__()
        self.client = client

    async def _list_resources(self) -> Sequence[Resource]:
        spaces = await self.client.list_spaces()
        return [self.make_resource(space.name) for space in spaces]

    def make_resource(self, name: str) -> Resource:
        async def read() -> str:
            info = await self.client.get_space(name)
            return info.model_dump_json()

        return FunctionResource.from_function(
            read,
            uri=space_uri(name),
            name=name,
            title=f"Space: {name}",
            description=f"Metadata and entry count of the '{name}' space.",
            mime_type="application/json",
        )
