from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers.sentence_transformer.modules import StaticEmbedding
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

from vexicon.embedding import HFEmbeddingFunction


def save_static_model(path: Path, prompts: dict[str, str]) -> str:
    """Save a tiny static-embedding model whose config declares the given prompts."""
    vocab = {"[UNK]": 0, "query": 1, "passage": 2, ":": 3, "cats": 4, "purr": 5}
    tokenizer = Tokenizer(WordLevel(vocab, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    weights = np.random.default_rng(0).normal(size=(len(vocab), 8))
    static = StaticEmbedding(tokenizer, embedding_weights=weights.astype(np.float32))
    SentenceTransformer(modules=[static], prompts=prompts).save(str(path))
    return str(path)


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
