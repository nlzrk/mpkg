# mpkg

Declarative, cross-distro package management for Linux. Write your packages once — mpkg installs them on any distro using the native package manager.

```yaml
# ~/.config/mpkg/packages.yaml
packages:
  - neovim
  - ripgrep
  - fd
  - git
```

```bash
mpkg sync   # installs everything, on any machine, with the right package names
```

On Ubuntu this runs `apt install fd-find`. On Arch it runs `pacman -S fd`. You never touch the distro-specific names.

---

## Why mpkg

If you manage multiple machines across different distros, you've probably maintained separate install scripts or had to remember that `fd` is called `fd-find` on Debian-based systems and `bat` is called `batcat`. mpkg replaces that with a single declarative config that travels with your dotfiles.

It is not a new package manager. It wraps the one you already have (apt, dnf, pacman) and adds:

- A portable config file as the source of truth
- Automatic name translation via the [Repology](https://repology.org) API
- A `sync` command to reproduce your package set on any machine

---

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/nlzrk/mpkg/main/install.sh | bash
```

The script will:
1. Check for Python 3.10+
2. Install mpkg via pip
3. Detect your package manager (apt / dnf / pacman)
4. If none is found, offer to install [Nix](https://nixos.org) as a universal fallback

**Manual install** (if you already have Python and pip):

```bash
pip install git+https://github.com/nlzrk/mpkg.git
```

---

## Supported backends

| Backend | Distros |
|---|---|
| apt | Ubuntu, Debian, and derivatives |
| dnf | Fedora, RHEL, and derivatives |
| pacman | Arch Linux and derivatives |
| nix | Any Linux distro (universal fallback) |

mpkg detects whichever is present. On a standard distro install your native package manager is already there — no setup needed.

---

## Commands

### `mpkg install <package>`

Installs a package and adds it to your config.

```bash
mpkg install neovim
mpkg install ripgrep
```

mpkg looks up the canonical name on Repology, finds the right name for your distro, and installs it via your native package manager. The config is updated automatically.

If the package is available on more than one detected backend, mpkg prompts you to pick:

```
Found 'fd' on multiple backends:
  [1] pacman     fd           9.0.0   → archlinux.org/packages/extra/x86_64/fd/
  [2] nix        fd           9.0.0   → search.nixos.org/packages?query=fd

Select backend [1-2]:
```

Your choice is saved as an override so future syncs use the same backend without asking.

---

### `mpkg remove <package>`

Removes a package and updates your config.

```bash
mpkg remove neovim
```

---

### `mpkg sync`

Reads your config and installs any missing packages on the current machine. This is the main command you run on a new machine.

```bash
mpkg sync
```

Packages already installed are skipped. Packages that can't be resolved for the current distro are warned and logged — they are never silently skipped without output.

```
Syncing 12 package(s) via apt…

  ✓ neovim already installed
  ✓ git already installed
  Installing ripgrep…
  [SKIP] fd — not found on apt
    Repology suggests: fd-find
    Add an override to your config or rename the entry.

Done. 10 installed (1 new), 1 skipped, 0 failed.
```

---

### `mpkg import`

Adopts packages you already have installed into your config. Only imports packages you explicitly installed — not auto-installed dependencies.

```bash
mpkg import           # shows what will be added, prompts for confirmation
mpkg import --yes     # non-interactive, useful in bootstrap scripts
mpkg import --prune   # also remove config entries for packages you've since uninstalled
```

Example output:

```
curl                new
fd-find             new
git                 new
neovim              already tracked
ripgrep             new

4 new, 1 already tracked

Note: names are distro-specific. On other distros some may not resolve
— run 'mpkg status' after syncing to a new machine.

Add 4 packages to config? [Y/n]
```

How "explicit only" works per backend:

| Backend | Method |
|---|---|
| apt | `apt-mark showmanual` |
| pacman | `pacman -Qe` |
| dnf | `dnf repoquery --userinstalled` |
| nix | all nix-env entries (all are explicit by design) |

---

### `mpkg search <package>`

Queries Repology and shows what the package is called across repos. No install happens.

```bash
mpkg search fd
```

```
           repology: fd
 Repo               Name       Version
 ──────────────────────────────────────
 arch                fd         9.0.0
 ubuntu_24_04        fd-find    9.0.0
 ubuntu_22_04        fd-find    8.7.0
 fedora_40           fd-find    9.0.0
 nix_unstable        fd         9.0.0
 …
```

Useful when a package fails to resolve and you need to figure out what it's called on your distro.

---

### `mpkg status`

Shows the state of every package in your config against what's actually installed.

```bash
mpkg status
```

```
 Package    Resolved name   Status
 ─────────────────────────────────
 neovim     neovim          installed
 ripgrep    ripgrep         installed
 fd         fd-find         missing
 mycli      —               unresolvable
```

- **installed** — in config and present on the system
- **missing** — in config but not installed (run `mpkg sync` to fix)
- **unresolvable** — mpkg can't find a match on Repology for this distro

---

### `mpkg setup-hooks`

Installs a hook into your package manager so the config updates automatically whenever you install or remove packages — even if you use `apt`/`pacman`/`dnf` directly instead of going through mpkg.

```bash
sudo mpkg setup-hooks
```

Must be run as root because it writes into system hook directories. It detects the current user from `$SUDO_USER` so the right config file is updated, not root's.

What gets installed per backend:

| Backend | Hook location |
|---|---|
| apt | `/etc/apt/apt.conf.d/99mpkg` |
| pacman | `/etc/pacman.d/hooks/mpkg.hook` |
| dnf | DNF plugin in the Python site-packages `dnf-plugins/` directory |

After setup, every `apt install`, `pacman -S`, or `dnf install` will automatically run `mpkg import --yes --prune` in the background, keeping your config file in sync without any extra steps.

---

## Config file

Location: `~/.config/mpkg/packages.yaml`

```yaml
version: 1

packages:
  - neovim
  - ripgrep
  - fd
  - git

overrides:
  fd:
    apt: fd-find
    dnf: fd-find

# auto-generated — do not edit
resolved:
  apt:
    fd:
      name: fd-find
      version: 8.7.0
```

**`packages`** — canonical package names. These are the names you care about, distro-agnostic.

**`overrides`** — maps a canonical name to the real package name on a specific backend. Written automatically when you resolve a multi-backend prompt or run `mpkg import`. You can also add them manually when a package has a known different name.

**`resolved`** — cache of the last successful resolution per backend. Auto-generated, don't edit.

You can edit `packages.yaml` directly and run `mpkg sync` — it's equivalent to using the CLI.

---

## Overrides

When a package name differs between distros, add an override:

```yaml
overrides:
  fd:
    apt: fd-find
    dnf: fd-find
  bat:
    apt: batcat
```

mpkg checks overrides before hitting the Repology API, so overrides also serve as a local cache when you know the correct name.

---

## Failure handling

When a package can't be resolved, mpkg warns and skips — it never silently falls back to Flatpak or Snap. Failures are also appended to `~/.config/mpkg/failed.log`:

```
2024-11-03T14:22:01  mycli  not found on apt
```

To fix a failed package:
1. Run `mpkg search <name>` to see what Repology calls it
2. Add an override to your config, or rename the entry in `packages`
3. Run `mpkg sync` again

---

## Dotfiles workflow

The intended use is committing `packages.yaml` alongside your dotfiles:

```bash
# On your main machine
mpkg import --yes
cp ~/.config/mpkg/packages.yaml ~/dotfiles/packages.yaml
git -C ~/dotfiles add packages.yaml && git commit -m "update packages"

# On a new machine
git clone <your-dotfiles> ~/dotfiles
ln -s ~/dotfiles/packages.yaml ~/.config/mpkg/packages.yaml
mpkg sync
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MPKG_CONFIG_DIR` | `~/.config/mpkg` | Override the config and log directory |
