import requests

_BASE = "https://repology.org/api/v1/project"
_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "mpkg/0.1 (https://github.com/nlzrk/mpkg)"
_cache: dict[str, list[dict]] = {}

# Repo name prefixes that map to each backend
_BACKEND_REPOS: dict[str, list[str]] = {
    "apt":    ["ubuntu", "debian"],
    "dnf":    ["fedora", "epel"],
    "pacman": ["arch"],
}


def _url_for(entry: dict, backend: str) -> str:
    name = entry.get("name", "")
    subrepo = entry.get("subrepo", "")
    if backend == "pacman":
        if subrepo:
            return f"https://archlinux.org/packages/{subrepo}/x86_64/{name}/"
        return f"https://archlinux.org/packages/search/?q={name}"
    if backend == "apt":
        return f"https://packages.ubuntu.com/{name}"
    if backend == "dnf":
        return f"https://packages.fedoraproject.org/pkgs/{name}/"
    return ""


def _fetch(name: str) -> list[dict]:
    if name not in _cache:
        resp = _SESSION.get(f"{_BASE}/{name}", timeout=15)
        resp.raise_for_status()
        _cache[name] = resp.json()
    return _cache[name]


def packages_for_backend(canonical: str, backend: str) -> list[dict]:
    """Return de-duplicated Repology entries for this backend, sorted newest-first."""
    patterns = _BACKEND_REPOS.get(backend, [])
    raw = _fetch(canonical)
    seen: set[str] = set()
    results: list[dict] = []
    for entry in raw:
        repo = entry.get("repo", "")
        if not any(repo.startswith(p) for p in patterns):
            continue
        pkg_name = entry.get("name", canonical)
        if pkg_name in seen:
            continue
        seen.add(pkg_name)
        results.append({
            "repo": repo,
            "name": pkg_name,
            "version": entry.get("version", ""),
            "url": _url_for(entry, backend),
            "backend": backend,
        })
    return results


def search_project(canonical: str) -> list[dict]:
    """Return all Repology entries for display (no filtering)."""
    raw = _fetch(canonical)
    return [
        {
            "repo": e.get("repo", ""),
            "name": e.get("name", canonical),
            "version": e.get("version", ""),
        }
        for e in raw
    ]
