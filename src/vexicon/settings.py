from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from vexicon.embedding import Device


def default_persistent_path() -> Path:
    """Returns ~/.vexicon/chroma, creating the directory when it is missing."""
    path = Path.home() / ".vexicon" / "chroma"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_index_db_path() -> Path:
    """Returns ~/.vexicon/hybrid.db, creating ~/.vexicon when it is missing."""
    path = Path.home() / ".vexicon" / "hybrid.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class Settings(BaseSettings):
    """Read from VEXICON_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="VEXICON_", extra="ignore")

    persistent_path: Path = Field(
        default_factory=default_persistent_path,
        description="Directory where the PersistentClient stores its DB.",
    )
    index_db_path: Path = Field(
        default_factory=default_index_db_path,
        description="SQLite database file holding the keyword index.",
    )
    vector_weight: float = Field(
        default=1.0, ge=0, description="Weight of the vector ranking in fusion."
    )
    keyword_weight: float = Field(
        default=1.0, ge=0, description="Weight of the FTS5 ranking in fusion."
    )
    rrf_rank_offset: int = Field(
        default=60, ge=1, description="Rank offset in reciprocal rank fusion."
    )
    device: Device = Field(
        default=Device.auto, description="Device that runs embedding models."
    )
    idle_seconds: float = Field(
        default=300.0,
        gt=0,
        description="Seconds without Chroma activity before the client and "
        "embedding models are unloaded.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
