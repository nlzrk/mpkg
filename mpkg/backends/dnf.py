import subprocess

from .base import Backend


class DnfBackend(Backend):
    name = "dnf"
    binary = "/usr/bin/dnf"

    def install(self, package: str) -> bool:
        return subprocess.run(["dnf", "install", "-y", package]).returncode == 0

    def remove(self, package: str) -> bool:
        return subprocess.run(["dnf", "remove", "-y", package]).returncode == 0

    def is_installed(self, package: str) -> bool:
        r = subprocess.run(
            ["dnf", "list", "installed", package],
            capture_output=True, text=True,
        )
        return r.returncode == 0

    def list_installed(self) -> set[str]:
        r = subprocess.run(
            ["dnf", "list", "installed"],
            capture_output=True, text=True,
        )
        pkgs: set[str] = set()
        for line in r.stdout.splitlines():
            parts = line.split()
            if parts and "." in parts[0]:
                pkgs.add(parts[0].rsplit(".", 1)[0])
        return pkgs

    def list_explicit(self) -> set[str]:
        # --userinstalled filters out auto-installed dependencies
        r = subprocess.run(
            ["dnf", "repoquery", "--userinstalled", "--queryformat", "%{name}"],
            capture_output=True, text=True,
        )
        return {line.strip() for line in r.stdout.splitlines() if line.strip() and not line.startswith("Last metadata")}
