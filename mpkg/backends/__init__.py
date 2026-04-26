from .apt import AptBackend
from .base import Backend
from .dnf import DnfBackend
from .nix import NixBackend
from .pacman import PacmanBackend

# Nix is last — native backends are preferred when available
_ALL: list[Backend] = [PacmanBackend(), AptBackend(), DnfBackend(), NixBackend()]


def detect_backends() -> list[Backend]:
    return [b for b in _ALL if b.is_available()]
