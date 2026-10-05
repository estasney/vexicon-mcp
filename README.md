# vexicon

General knowledge store served over MCP. Notes and reference material live in
named spaces backed by Chroma collections with a SQLite FTS5 keyword index;
searches fuse the vector and keyword rankings by reciprocal rank fusion.

Run the server over stdio with `uv run vexicon`.

Settings are read from `VEXICON_*` environment variables; see
`src/vexicon/settings.py`. `VEXICON_PERSISTENT_PATH` and
`VEXICON_INDEX_DB_PATH` are required.
