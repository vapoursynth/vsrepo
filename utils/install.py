from typing import NamedTuple


class InstallFileResult(NamedTuple):
    success: int
    error: int

    def __add__(self, other: 'InstallFileResult') -> 'InstallFileResult':  # type: ignore[override]
        return InstallFileResult(*map(lambda x, y: x + y, self, other))
