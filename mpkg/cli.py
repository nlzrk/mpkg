import argparse
import sys

import requests
from rich.console import Console
from rich.table import Table

from . import config as cfg
from . import logger, repology, resolver
from .backends import detect_backends

console = Console()


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

def cmd_install(args: argparse.Namespace) -> None:
    config = cfg.load()
    canonical: str = args.package

    backends = detect_backends()
    if not backends:
        console.print("[red]No supported package manager found (apt/dnf/pacman).[/red]")
        sys.exit(1)

    # Gather (backend, best_entry) pairs for every backend that has the package
    options: list[tuple] = []
    for backend in backends:
        candidates = resolver.resolve_with_candidates(canonical, backend, config)
        if candidates:
            options.append((backend, candidates[0]))

    if not options:
        _warn_not_found(canonical)
        logger.log_failure(canonical, "not found on any detected backend")
        return

    if len(options) == 1:
        selected_backend, selected_pkg = options[0]
    else:
        selected_backend, selected_pkg = _prompt_backend(canonical, options)
        cfg.write_override(config, canonical, selected_backend.name, selected_pkg["name"])

    pkg_name: str = selected_pkg["name"]
    version: str = selected_pkg.get("version", "")

    console.print(f"Installing [bold]{pkg_name}[/bold] via [bold]{selected_backend.name}[/bold]…")
    if selected_backend.install(pkg_name):
        cfg.add_package(config, canonical)
        cfg.write_resolved(config, selected_backend.name, canonical, pkg_name, version)
        cfg.save(config)
        console.print(f"[green]✓[/green] {canonical} installed.")
    else:
        console.print(f"[red]✗[/red] Failed to install {canonical}.")
        logger.log_failure(canonical, f"install failed via {selected_backend.name}")


def _prompt_backend(canonical: str, options: list[tuple]) -> tuple:
    console.print(f"\nFound '[bold]{canonical}[/bold]' on multiple backends:")
    for i, (backend, pkg) in enumerate(options, 1):
        name = pkg["name"]
        ver = pkg.get("version", "")
        url = pkg.get("url", "")
        console.print(f"  [{i}] {backend.name:<10} {name:<20} {ver:<12} → {url}")

    while True:
        raw = console.input(f"\nSelect backend [1-{len(options)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        console.print(f"[red]Enter a number between 1 and {len(options)}.[/red]")


def _warn_not_found(canonical: str) -> None:
    console.print(f"[yellow][SKIP][/yellow] {canonical} — not found on any detected backend")
    try:
        entries = repology.search_project(canonical)
        if entries:
            names = list(dict.fromkeys(e["name"] for e in entries[:5]))
            console.print(f"  Repology suggests: {', '.join(names)}")
    except Exception:
        pass
    console.print("  Add an override to your config or rename the entry.")


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

def cmd_remove(args: argparse.Namespace) -> None:
    config = cfg.load()
    canonical: str = args.package

    if canonical not in config["packages"]:
        console.print(f"[yellow]{canonical}[/yellow] is not in your config.")
        return

    backends = detect_backends()
    if not backends:
        console.print("[red]No supported package manager found.[/red]")
        sys.exit(1)

    backend = backends[0]
    pkg_name = resolver.resolve(canonical, backend, config) or canonical

    console.print(f"Removing [bold]{pkg_name}[/bold] via [bold]{backend.name}[/bold]…")
    if backend.remove(pkg_name):
        cfg.remove_package(config, canonical)
        for distro_map in config.get("resolved", {}).values():
            distro_map.pop(canonical, None)
        cfg.save(config)
        console.print(f"[green]✓[/green] {canonical} removed.")
    else:
        console.print(f"[red]✗[/red] Failed to remove {canonical}.")


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

def cmd_sync(_args: argparse.Namespace) -> None:
    config = cfg.load()
    packages: list[str] = config.get("packages", [])

    if not packages:
        console.print("No packages in config.")
        return

    backends = detect_backends()
    if not backends:
        console.print("[red]No supported package manager found.[/red]")
        sys.exit(1)

    backend = backends[0]
    console.print(f"Syncing {len(packages)} package(s) via [bold]{backend.name}[/bold]…\n")

    installed_set = backend.list_installed()
    already = skipped = failed = installed = 0

    for canonical in packages:
        # Check resolved cache before hitting Repology
        cached_name = cfg.get_resolved_name(config, backend.name, canonical)
        if cached_name and cached_name in installed_set:
            console.print(f"  [dim]✓ {canonical} already installed[/dim]")
            already += 1
            continue

        entries = resolver.resolve_with_candidates(canonical, backend, config)
        if not entries:
            console.print(f"  [yellow][SKIP][/yellow] {canonical} — not found on {backend.name}")
            try:
                suggestions = repology.search_project(canonical)
                if suggestions:
                    names = list(dict.fromkeys(e["name"] for e in suggestions[:3]))
                    console.print(f"    Repology suggests: {', '.join(names)}")
            except Exception:
                pass
            logger.log_failure(canonical, f"not found on {backend.name}")
            skipped += 1
            continue

        pkg_name = entries[0]["name"]
        if pkg_name in installed_set:
            console.print(f"  [dim]✓ {canonical} already installed[/dim]")
            cfg.write_resolved(config, backend.name, canonical, pkg_name, entries[0].get("version", ""))
            already += 1
            continue

        console.print(f"  Installing [bold]{pkg_name}[/bold]…")
        if backend.install(pkg_name):
            cfg.write_resolved(config, backend.name, canonical, pkg_name, entries[0].get("version", ""))
            installed += 1
        else:
            console.print(f"  [red]✗[/red] Failed to install {canonical}")
            logger.log_failure(canonical, f"install failed via {backend.name}")
            failed += 1

    cfg.save(config)
    console.print(
        f"\n[green]Done.[/green] "
        f"{already + installed} installed ({installed} new), "
        f"{skipped} skipped, {failed} failed."
    )


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------

def cmd_import(args: argparse.Namespace) -> None:
    config = cfg.load()

    backends = detect_backends()
    if not backends:
        console.print("[red]No supported package manager found.[/red]")
        sys.exit(1)

    backend = backends[0]
    console.print(f"Scanning explicitly installed packages via [bold]{backend.name}[/bold]…\n")

    explicit = backend.list_explicit()
    if not explicit:
        console.print("[yellow]No explicitly installed packages found.[/yellow]")
        return

    already = {p for p in config["packages"] if p in explicit}
    new_pkgs = sorted(explicit - set(config["packages"]))

    if not new_pkgs:
        console.print(f"All {len(already)} explicit packages are already in config.")
        return

    table = Table(show_lines=False, box=None, pad_edge=False)
    table.add_column("Package", style="cyan")
    table.add_column("", style="dim")

    for pkg in new_pkgs:
        table.add_row(pkg, "new")
    for pkg in sorted(already):
        table.add_row(pkg, "already tracked")

    console.print(table)
    console.print(
        f"\n[bold]{len(new_pkgs)}[/bold] new, "
        f"[dim]{len(already)} already tracked[/dim]\n"
    )
    console.print(
        "[dim]Note: names are distro-specific. On other distros some may not resolve "
        "— run 'mpkg status' after syncing to a new machine.[/dim]\n"
    )

    if not args.yes:
        reply = console.input(f"Add {len(new_pkgs)} packages to config? [Y/n] ").strip()
        if reply and reply.lower() != "y":
            console.print("Aborted.")
            return

    for pkg in new_pkgs:
        cfg.add_package(config, pkg)
        cfg.write_override(config, pkg, backend.name, pkg)

    cfg.save(config)
    console.print(f"[green]✓[/green] Added {len(new_pkgs)} packages to config.")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def cmd_search(args: argparse.Namespace) -> None:
    canonical: str = args.package
    console.print(f"Searching Repology for '[bold]{canonical}[/bold]'…\n")

    try:
        entries = repology.search_project(canonical)
    except requests.RequestException as exc:
        console.print(f"[red]Repology request failed:[/red] {exc}")
        sys.exit(1)

    if not entries:
        console.print("No results found.")
        return

    table = Table(title=f"repology: {canonical}", show_lines=False)
    table.add_column("Repo", style="cyan", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Version", style="green")

    for e in entries[:40]:
        table.add_row(e["repo"], e["name"], e["version"])

    console.print(table)
    if len(entries) > 40:
        console.print(f"[dim]… and {len(entries) - 40} more.[/dim]")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(_args: argparse.Namespace) -> None:
    config = cfg.load()
    packages: list[str] = config.get("packages", [])

    if not packages:
        console.print("No packages in config.")
        return

    backends = detect_backends()
    if not backends:
        console.print("[red]No supported package manager found.[/red]")
        sys.exit(1)

    backend = backends[0]
    console.print(f"Checking status via [bold]{backend.name}[/bold]…\n")

    installed_set = backend.list_installed()

    table = Table(show_lines=False)
    table.add_column("Package", style="cyan")
    table.add_column("Resolved name", style="white")
    table.add_column("Status")

    for canonical in packages:
        pkg_name = resolver.resolve(canonical, backend, config)
        if pkg_name is None:
            table.add_row(canonical, "[dim]—[/dim]", "[yellow]unresolvable[/yellow]")
        elif pkg_name in installed_set:
            table.add_row(canonical, pkg_name, "[green]installed[/green]")
        else:
            table.add_row(canonical, pkg_name, "[red]missing[/red]")

    console.print(table)


# ---------------------------------------------------------------------------
# entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mpkg",
        description="Declarative cross-distro package manager wrapper",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("install", help="Install a package and add to config")
    p.add_argument("package")

    p = sub.add_parser("remove", help="Remove a package and update config")
    p.add_argument("package")

    sub.add_parser("sync", help="Install all packages declared in config")

    p = sub.add_parser("search", help="Search Repology without installing")
    p.add_argument("package")

    sub.add_parser("status", help="Diff config vs currently installed packages")

    p = sub.add_parser("import", help="Import explicitly installed packages into config")
    p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()
    {
        "install": cmd_install,
        "remove":  cmd_remove,
        "sync":    cmd_sync,
        "search":  cmd_search,
        "status":  cmd_status,
        "import":  cmd_import,
    }[args.command](args)


if __name__ == "__main__":
    main()
