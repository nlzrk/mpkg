from .apt import AptBackend
from .base import Backend
from .dnf import DnfBackend
from .pacman import PacmanBackend

_ALL: list[Backend] = [PacmanBackend(), AptBackend(), DnfBackend()]


def detect_backends() -> list[Backend]:
    return [b for b in _ALL if b.is_available()]
