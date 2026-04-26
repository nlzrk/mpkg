import shutil
import subprocess

from .base import Backend


class NixBackend(Backend):
    name = "nix"
    binary = ""  # nix-env may be in several locations; use shutil.which

    def is_available(self) -> bool:
        return shutil.which("nix-env") is not None

    def install(self, package: str) -> bool:
        return subprocess.run(["nix-env", "-iA", f"nixpkgs.{package}"]).returncode == 0

    def remove(self, package: str) -> bool:
        return subprocess.run(["nix-env", "-e", package]).returncode == 0

    def is_installed(self, package: str) -> bool:
        r = subprocess.run(["nix-env", "-q", package], capture_output=True, text=True)
        return r.returncode == 0 and package in r.stdout

    def list_installed(self) -> set[str]:
        r = subprocess.run(["nix-env", "-q", "--json"], capture_output=True, text=True)
        if r.returncode != 0:
            return set()
        import json
        try:
            data = json.loads(r.stdout)
            return {attrs.get("pname", "") for attrs in data.values() if attrs.get("pname")}
        except (json.JSONDecodeError, AttributeError):
            return set()
