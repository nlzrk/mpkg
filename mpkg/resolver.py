from . import repology
from .backends.base import Backend


def resolve(canonical: str, backend: Backend, config: dict) -> str | None:
    """Return the install-time package name, or None if unresolvable."""
    override = config.get("overrides", {}).get(canonical, {}).get(backend.name)
    if override:
        return override
    try:
        entries = repology.packages_for_backend(canonical, backend.name)
    except Exception:
        return None
    return entries[0]["name"] if entries else None


def resolve_with_candidates(canonical: str, backend: Backend, config: dict) -> list[dict] | None:
    """Return all candidate entries for this backend, or None if none found."""
    override = config.get("overrides", {}).get(canonical, {}).get(backend.name)
    if override:
        return [{"name": override, "version": "", "url": "", "repo": "override", "backend": backend.name}]
    try:
        entries = repology.packages_for_backend(canonical, backend.name)
    except Exception:
        return None
    return entries if entries else None
