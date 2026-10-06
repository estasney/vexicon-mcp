class VexiconError(Exception):
    pass


class SpaceNotIndexedError(VexiconError):
    def __init__(self, space: str) -> None:
        super().__init__(f"Space {space!r} is not indexed")
        self.space = space


class DuplicateEntryIdsError(VexiconError):
    def __init__(self) -> None:
        super().__init__("Entry IDs repeat within the batch")


class InvalidFilterError(VexiconError):
    pass


class EntriesExistError(VexiconError):
    def __init__(self, space: str, ids: list[str]) -> None:
        super().__init__(f"Entry IDs already exist in {space!r}: " + ", ".join(ids))
        self.space = space
        self.ids = ids
