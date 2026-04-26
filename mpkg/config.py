import os
from pathlib import Path
from typing import Any

import yaml

_config_dir = Path(os.environ.get("MPKG_CONFIG_DIR", "~/.config/mpkg")).expanduser()
_config_file = _config_dir / "packages.yaml"

_DEFAULT: dict[str, Any] = {
    "version": 1,
    "packages": [],
    "overrides": {},
    "resolved": {},
}


def load() -> dict:
    if not _config_file.exists():
        return {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
                for k, v in _DEFAULT.items()}
    with open(_config_file) as f:
        data = yaml.safe_load(f) or {}
    for key, default in _DEFAULT.items():
        data.setdefault(key, type(default)())
    return data


def save(config: dict) -> None:
    _config_dir.mkdir(parents=True, exist_ok=True)
    with open(_config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def add_package(config: dict, name: str) -> bool:
    if name not in config["packages"]:
        config["packages"].append(name)
        return True
    return False


def remove_package(config: dict, name: str) -> bool:
    if name in config["packages"]:
        config["packages"].remove(name)
        return True
    return False


def write_override(config: dict, canonical: str, backend: str, pkg_name: str) -> None:
    config.setdefault("overrides", {}).setdefault(canonical, {})[backend] = pkg_name


def write_resolved(config: dict, backend: str, canonical: str, pkg_name: str, version: str) -> None:
    config.setdefault("resolved", {}).setdefault(backend, {})[canonical] = {
        "name": pkg_name,
        "version": version,
    }


def get_resolved_name(config: dict, backend: str, canonical: str) -> str | None:
    return config.get("resolved", {}).get(backend, {}).get(canonical, {}).get("name")
