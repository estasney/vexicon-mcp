from pathlib import Path

import numpy as np
import pytest
from sentence_transformers import SentenceTransformer
from sentence_transformers.sentence_transformer.modules import StaticEmbedding
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace


def save_static_model(path: Path, prompts: dict[str, str]) -> str:
    """Save a tiny static-embedding model whose config declares the given prompts."""
    vocab = {"[UNK]": 0, "query": 1, "passage": 2, ":": 3, "cats": 4, "purr": 5}
    tokenizer = Tokenizer(WordLevel(vocab, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    weights = np.random.default_rng(0).normal(size=(len(vocab), 8))
    static = StaticEmbedding(tokenizer, embedding_weights=weights.astype(np.float32))
    SentenceTransformer(modules=[static], prompts=prompts).save(str(path))
    return str(path)


@pytest.fixture
def static_model(tmp_path: Path) -> str:
    return save_static_model(tmp_path / "model", {})
