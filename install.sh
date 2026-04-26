#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${BOLD}==> $*${RESET}"; }
success() { echo -e "${GREEN}✓ $*${RESET}"; }
warn()    { echo -e "${YELLOW}! $*${RESET}"; }
die()     { echo -e "${RED}✗ $*${RESET}" >&2; exit 1; }

# ── Python ────────────────────────────────────────────────────────────────────

info "Checking Python..."
if ! command -v python3 &>/dev/null; then
    die "Python 3 not found. Install Python 3.10+ and re-run this script."
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ]]; then
    die "Python 3.10+ required (found $PY_VERSION)."
fi
success "Python $PY_VERSION"

# ── mpkg ─────────────────────────────────────────────────────────────────────

info "Installing mpkg..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    # Running from a local checkout
    pip install --quiet "$SCRIPT_DIR"
else
    pip install --quiet "git+https://github.com/nlzrk/mpkg.git"
fi

success "mpkg installed ($(mpkg --version 2>/dev/null || echo 'ok'))"

# ── Backend detection ─────────────────────────────────────────────────────────

info "Detecting package manager backends..."

BACKENDS=()
command -v pacman  &>/dev/null && BACKENDS+=("pacman")
command -v apt     &>/dev/null && BACKENDS+=("apt")
command -v dnf     &>/dev/null && BACKENDS+=("dnf")
command -v nix-env &>/dev/null && BACKENDS+=("nix")

if [[ ${#BACKENDS[@]} -gt 0 ]]; then
    success "Found: ${BACKENDS[*]}"
    echo ""
    echo -e "  ${BOLD}mpkg is ready.${RESET} Try:"
    echo "    mpkg search neovim"
    echo "    mpkg install ripgrep"
    exit 0
fi

# ── No backend found — offer Nix ─────────────────────────────────────────────

echo ""
warn "No supported package manager found (apt / dnf / pacman / nix)."
echo ""
echo "  mpkg can install Nix — a universal package manager that works on any"
echo "  Linux distro without touching your system packages. It has 80,000+"
echo "  packages and coexists safely alongside any native package manager."
echo ""
read -rp "  Install Nix now? [Y/n] " REPLY
REPLY="${REPLY:-Y}"

if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
    warn "Skipped. mpkg is installed but has no backend to install packages with."
    echo "  Install Nix later with:  curl -L https://nixos.org/nix/install | sh"
    exit 0
fi

echo ""
info "Installing Nix..."

if [[ "$(id -u)" -eq 0 ]]; then
    # Root: multi-user (daemon) install
    sh <(curl -fsSL https://nixos.org/nix/install) --daemon
else
    # Non-root: single-user install
    sh <(curl -fsSL https://nixos.org/nix/install) --no-daemon
fi

echo ""
success "Nix installed."
echo ""
echo "  To activate Nix in your current shell, run:"
echo ""

if [[ -f "$HOME/.nix-profile/etc/profile.d/nix.sh" ]]; then
    echo "    source \$HOME/.nix-profile/etc/profile.d/nix.sh"
elif [[ -f "/etc/profile.d/nix.sh" ]]; then
    echo "    source /etc/profile.d/nix.sh"
fi

echo ""
echo "  Then mpkg is fully ready:"
echo "    mpkg search neovim"
echo "    mpkg install ripgrep"
