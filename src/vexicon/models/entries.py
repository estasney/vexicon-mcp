from datetime import UTC, datetime

from pydantic import BaseModel, Field, computed_field
from pydantic.json_schema import SkipJsonSchema

from vexicon.models.base import Metadata, SpaceName, current_epoch_second


class NewEntry(BaseModel):
    text: str = Field(
        description="Entry text within half of the space's embedding_max_tokens."
    )
    id: str = Field(
        description="Kebab-case mnemonic ID.",
        min_length=1,
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
    )
    meta: Metadata | None = Field(default=None, description="Entry metadata.")
    created_at: SkipJsonSchema[int] = Field(default_factory=current_epoch_second)


class UpdateEntriesInput(BaseModel):
    ids: list[str] = Field(description="IDs of entries to update.")
    space: SpaceName
    metadata: list[Metadata] | None = Field(
        default=None, description="New metadata per ID."
    )
    texts: list[str] | None = Field(default=None, description="New entry text per ID.")


class Entry(BaseModel):
    id: str = Field(description="Entry ID.")
    text: str | None = Field(description="Entry text.")
    metadata_raw: Metadata | None = Field(exclude=True)

    @computed_field(description="When the entry was stored.")
    @property
    def created(self) -> datetime | None:
        match (self.metadata_raw or {}).get("created_at"):
            case int() | float() as created_at:
                return datetime.fromtimestamp(created_at, tz=UTC)
            case _:
                return None

    @computed_field(description="Other entry metadata.")
    @property
    def metadata(self) -> Metadata | None:
        rest = {
            key: value
            for key, value in (self.metadata_raw or {}).items()
            if key != "created_at"
        }
        return rest or None
