import asyncio
from typing import Annotated

from fastmcp.server.context import Context
from fastmcp.tools import ToolResult
from huggingface_hub import CachedRepoInfo, HfApi, ModelInfo, scan_cache_dir
from pydantic import Field

from vexicon.models.embeddings import EmbeddingModel, HubRepoId
from vexicon.text_tools import lines_tool, plain_tool, table_tool


def is_sentence_transformer(repo: CachedRepoInfo) -> bool:
    markers = {"modules.json", "config_sentence_transformers.json"}
    filenames = {file.file_name for rev in repo.revisions for file in rev.files}
    return repo.repo_type == "model" and bool(filenames & markers)


def list_local_repo_ids() -> list[str]:
    """Return repo_ids of sentence-transformer models cached locally."""
    repos = scan_cache_dir().repos
    return sorted(repo.repo_id for repo in repos if is_sentence_transformer(repo))


def list_hub_models(limit: int) -> list[ModelInfo]:
    models = HfApi().list_models(
        author="sentence-transformers",
        sort="downloads",
        limit=limit,
        expand=["downloads"],
    )
    return list(models)


@lines_tool
async def list_embedding_models(ctx: Context) -> list[str]:
    """List the embedding model repo_ids that create_space accepts."""
    return await asyncio.to_thread(list_local_repo_ids)


@table_tool
async def list_hub_embedding_models(
    ctx: Context, limit: Annotated[int, Field(ge=1)] = 20
) -> list[EmbeddingModel]:
    """List the most downloaded sentence-transformers models on Hugging Face."""
    found = await asyncio.to_thread(list_hub_models, limit)
    cached = set(await asyncio.to_thread(list_local_repo_ids))
    return [
        EmbeddingModel(repo_id=m.id, downloads=m.downloads, cached=m.id in cached)
        for m in found
    ]


@plain_tool
async def download_embedding_model(repo_id: HubRepoId, ctx: Context) -> ToolResult:
    """Download an embedding model so that create_space can use it."""
    if repo_id in await asyncio.to_thread(list_local_repo_ids):
        return ToolResult(content=f"Model {repo_id!r} is already downloaded.")
    from sentence_transformers import SentenceTransformer

    await asyncio.to_thread(SentenceTransformer, repo_id, local_files_only=False)
    return ToolResult(content=f"Downloaded model {repo_id!r}.")


EMBEDDING_TOOLS = [
    list_embedding_models,
    list_hub_embedding_models,
    download_embedding_model,
]
