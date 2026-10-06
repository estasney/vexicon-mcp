from typing import Annotated

from pydantic import BaseModel, Field, computed_field

from vexicon.models.base import ForbiddenKeys, Metadata
from vexicon.models.entries import Entry

SpaceMetadata = Annotated[
    Metadata,
    ForbiddenKeys(frozenset({"readme", "embedding_repo_id", "embedding_max_tokens"})),
]


class SpaceSummary(BaseModel):
    name: str = Field(description="Space name.")
    metadata_raw: Metadata | None = Field(exclude=True)

    @computed_field(
        description="What the space holds and the conventions its entries follow."
    )
    @property
    def readme(self) -> str | None:
        match (self.metadata_raw or {}).get("readme"):
            case str() as value:
                return value
            case _:
                return None

    @computed_field(description="Token cap per entry before truncation.")
    @property
    def embedding_max_tokens(self) -> int | None:
        match (self.metadata_raw or {}).get("embedding_max_tokens"):
            case int() as value:
                return value
            case _:
                return None

    @computed_field(description="Embedding model set at creation.")
    @property
    def embedding_repo_id(self) -> str | None:
        match (self.metadata_raw or {}).get("embedding_repo_id"):
            case str() as value:
                return value
            case _:
                return None


class SpaceInfo(SpaceSummary):
    id: str = Field(description="Space ID.")
    count: int = Field(description="Number of entries stored.")

    @computed_field(description="Other space metadata.")
    @property
    def metadata(self) -> Metadata | None:
        known = {"readme", "embedding_max_tokens", "embedding_repo_id"}
        rest = {
            key: value
            for key, value in (self.metadata_raw or {}).items()
            if key not in known
        }
        return rest or None


class SpaceDescription(SpaceInfo):
    sample: list[Entry] = Field(description="The first few entries.")
