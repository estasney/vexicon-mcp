from pathlib import Path

import pytest

from vexicon import (
    Device,
    DuplicateEntryIdsError,
    EntriesExistError,
    HybridClient,
    NewEntry,
    SpaceNotIndexedError,
)


def open_client(root: Path) -> HybridClient:
    return HybridClient(
        root / "chroma", root / "hybrid.db", device=Device.cpu, idle_seconds=60
    )


def test_space_and_entry_round_trip(tmp_path: Path, static_model: str) -> None:
    with open_client(tmp_path) as client:
        space = client.create_space(
            "notes", readme="Cat facts.", embedding_repo_id=static_model
        )
        assert space.readme == "Cat facts."
        assert space.embedding_repo_id == static_model

        client.add_entries(
            "notes",
            [
                NewEntry(id="cats", text="cats purr", meta={"kind": "fact"}),
                NewEntry(id="other", text="query"),
            ],
        )
        assert client.get_space("notes").count == 2

        hits = client.search("notes", ["cats purr"], limit=1)
        assert [hit.id for hit in hits] == ["cats"]
        assert hits[0].metadata == {"kind": "fact"}
        assert hits[0].created is not None

        filtered = client.list_entries("notes", where={"kind": "fact"})
        assert [entry.id for entry in filtered] == ["cats"]

        client.update_entries("notes", ["other"], texts=["cats"])
        assert client.list_entries("notes", ids=["other"])[0].text == "cats"

        client.delete_entries("notes", ["other"])
        description = client.describe_space("notes", sample_size=5)
        assert description.count == 1
        assert [entry.id for entry in description.sample] == ["cats"]

        client.update_space("notes", new_name="facts", metadata={"owner": "eric"})
        assert [space.name for space in client.list_spaces()] == ["facts"]
        assert client.get_space("facts").metadata == {"owner": "eric"}

    with open_client(tmp_path) as client:
        assert [hit.id for hit in client.search("facts", ["purr"])] == ["cats"]
        client.delete_space("facts")
        assert client.list_spaces() == []


def test_entry_errors(tmp_path: Path, static_model: str) -> None:
    with open_client(tmp_path) as client:
        client.create_space("notes", embedding_repo_id=static_model)
        client.add_entries("notes", [NewEntry(id="cats", text="cats purr")])

        with pytest.raises(EntriesExistError):
            client.add_entries("notes", [NewEntry(id="cats", text="again")])
        with pytest.raises(DuplicateEntryIdsError):
            client.add_entries(
                "notes", [NewEntry(id="a", text="x"), NewEntry(id="a", text="y")]
            )
        with pytest.raises(SpaceNotIndexedError):
            client.search("missing", ["cats"])


def test_calls_before_enter_are_rejected(tmp_path: Path) -> None:
    client = open_client(tmp_path)
    with pytest.raises(RuntimeError):
        client.list_spaces()
