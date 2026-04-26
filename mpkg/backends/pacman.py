import subprocess

from .base import Backend


class PacmanBackend(Backend):
    name = "pacman"
    binary = "/usr/bin/pacman"

    def install(self, package: str) -> bool:
        return subprocess.run(["pacman", "-S", "--noconfirm", package]).returncode == 0

    def remove(self, package: str) -> bool:
        return subprocess.run(["pacman", "-Rs", "--noconfirm", package]).returncode == 0

    def is_installed(self, package: str) -> bool:
        return subprocess.run(
            ["pacman", "-Q", package],
            capture_output=True,
        ).returncode == 0

    def list_installed(self) -> set[str]:
        r = subprocess.run(["pacman", "-Q"], capture_output=True, text=True)
        return {line.split()[0] for line in r.stdout.splitlines() if line.split()}
