from pathlib import Path

import numpy as np
from conftest import save_static_model
from sentence_transformers import SentenceTransformer

from vexicon.embedding import HFEmbeddingFunction


def test_prompted_model_embeds_queries_and_entries_differently(
    tmp_path: Path,
) -> None:
    repo_id = save_static_model(tmp_path, {"query": "query: ", "document": "passage: "})
    embedding_function = HFEmbeddingFunction(repo_id, device="cpu")

    query = embedding_function.embed_query(["cats purr"])
    document = embedding_function(["cats purr"])

    assert not np.allclose(query, document)


def test_unprompted_model_embeds_queries_and_entries_as_before(
    tmp_path: Path,
) -> None:
    repo_id = save_static_model(tmp_path, {})
    embedding_function = HFEmbeddingFunction(repo_id, device="cpu")
    plain = SentenceTransformer(repo_id, device="cpu").encode(
        ["cats purr"], normalize_embeddings=True
    )

    np.testing.assert_array_equal(embedding_function.embed_query(["cats purr"]), plain)
    np.testing.assert_array_equal(embedding_function(["cats purr"]), plain)
