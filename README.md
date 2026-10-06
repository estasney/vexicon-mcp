# vexicon

## About

Hybrid knowledge store, usable as a Python library or as an MCP server.

Notes and reference material live in named spaces backed by Chroma
collections. Each space also has a SQLite FTS5 keyword index, and searches
fuse the vector and keyword rankings with reciprocal rank fusion, tunable
through settings.

vexicon ships opinionated defaults, listed under Defaults below.

Run the server over stdio with `uvx "vexicon[mcp]"`.

## Use as a library

Install `vexicon` without extras. `HybridClient` takes the same settings as
the server, as constructor arguments, and must be entered before use.
Entering migrates the keyword index and rebuilds it from Chroma.

```python
from pathlib import Path

from vexicon import HybridClient, NewEntry

with HybridClient(Path("~/.vexicon/chroma"), Path("~/.vexicon/hybrid.db")) as client:
    client.create_space("notes", readme="Short facts.")
    client.add_entries("notes", [NewEntry(id="cats-purr", text="Cats purr.")])
    for entry in client.search("notes", ["purring"], limit=5):
        print(entry.id, entry.text)
```

`AsyncHybridClient` has the same methods as coroutines and is entered with
`async with`. Both raise `VexiconError` subclasses for caller mistakes such
as a duplicate entry ID or a filter Chroma would reject.

## Add to an MCP client

The first launch downloads vexicon's dependencies, which can take longer than
a client's startup timeout. Each client below shows how to raise it.

### Claude Code

```sh
claude mcp add --scope user vexicon -- uvx "vexicon[mcp]"
```

Pass settings with `-e`:

```sh
claude mcp add --scope user vexicon -e VEXICON_DEVICE=cpu -- uvx "vexicon[mcp]"
```

Claude Code's startup timeout is 30 seconds. Raise it with `MCP_TIMEOUT` in
milliseconds:

```sh
MCP_TIMEOUT=120000 claude
```

### Codex

```sh
codex mcp add vexicon -- uvx "vexicon[mcp]"
```

Pass settings with `--env`:

```sh
codex mcp add vexicon --env VEXICON_DEVICE=cpu -- uvx "vexicon[mcp]"
```

Codex's startup timeout is 10 seconds. Raise it in `~/.codex/config.toml`:

```toml
[mcp_servers.vexicon]
command = "uvx"
args = ["vexicon[mcp]"]
startup_timeout_sec = 120
```

## Settings

| Variable                  | Default                | Meaning                                                                   |
|---------------------------|------------------------|---------------------------------------------------------------------------|
| `VEXICON_PERSISTENT_PATH` | `~/.vexicon/chroma`    | Directory where Chroma stores its database.                               |
| `VEXICON_INDEX_DB_PATH`   | `~/.vexicon/hybrid.db` | SQLite file holding the keyword index.                                    |
| `VEXICON_VECTOR_WEIGHT`   | `1.0`                  | Weight of the vector ranking in fusion.                                   |
| `VEXICON_KEYWORD_WEIGHT`  | `1.0`                  | Weight of the keyword ranking in fusion.                                  |
| `VEXICON_RRF_RANK_OFFSET` | `60`                   | Rank offset in reciprocal rank fusion.                                    |
| `VEXICON_DEVICE`          | `auto`                 | Device that runs embedding models: `auto`, `cpu`, or `cuda`.              |
| `VEXICON_IDLE_SECONDS`    | `300`                  | Seconds without activity before Chroma and embedding models are unloaded. |

## Compared with chroma-mcp

Compared against chroma-mcp 0.2.6 and chromadb 1.5.9.

### Hybrid search without Chroma Cloud

- vexicon combines vector and BM25 keyword rankings with reciprocal rank
  fusion, using a SQLite FTS5 index beside each local Chroma collection.

### Token usage

- vexicon's tool definitions take about 30% fewer tokens than chroma-mcp's.
- `search` returns at most `limit` entries in total, while chroma-mcp returns
  `n_results` per query, so its response grows with every query a model adds.
- Results always leave out embedding vectors, which add tokens without giving
  a model anything it can use.

### Embedding models

- Each space can use any sentence-transformers model, and tools let a model
  find and download one from Hugging Face.
- Cached models load without network calls.
- Models trained with separate query and document prompts get the matching
  prompt for searches and for stored entries.
- Spaces always have their embedding model's max token size available in
  metadata for sizing entries before they are added.

### Memory

- Embedding models unload from memory after `VEXICON_IDLE_SECONDS` without
  use.

### Defaults

- Storage persists under `~/.vexicon` by default.
- Entry IDs are kebab-case mnemonics.
- Duplicate entry IDs raise an error.
- Spaces are published as MCP resources.
- Chroma telemetry is off.

vexicon keeps its own fields in Chroma metadata:

- Each entry's metadata holds `created_at` in epoch seconds for recency
  filters in `where`.
- Each space's metadata holds its `readme`, `embedding_repo_id`, and
  `embedding_max_tokens`.
- Callers cannot set those three keys through a space's `metadata` argument.
- Tool results show these fields apart from the caller's own metadata.
