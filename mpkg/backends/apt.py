import subprocess

from .base import Backend


class AptBackend(Backend):
    name = "apt"
    binary = "/usr/bin/apt"

    def install(self, package: str) -> bool:
        return subprocess.run(["apt", "install", "-y", package]).returncode == 0

    def remove(self, package: str) -> bool:
        return subprocess.run(["apt", "remove", "-y", package]).returncode == 0

    def is_installed(self, package: str) -> bool:
        r = subprocess.run(
            ["dpkg-query", "-W", "-f=${Status}", package],
            capture_output=True, text=True,
        )
        # status field (4th word) is "installed" regardless of want/flag fields
        return r.returncode == 0 and r.stdout.split()[-1:] == ["installed"]

    def list_installed(self) -> set[str]:
        r = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package} ${Status}\n"],
            capture_output=True, text=True,
        )
        pkgs: set[str] = set()
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[3] == "installed":
                pkgs.add(parts[0])
        return pkgs

    def list_explicit(self) -> set[str]:
        r = subprocess.run(["apt-mark", "showmanual"], capture_output=True, text=True)
        return {line.strip() for line in r.stdout.splitlines() if line.strip()}
