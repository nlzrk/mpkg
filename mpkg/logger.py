import datetime
import os
from pathlib import Path

_log_dir = Path(os.environ.get("MPKG_CONFIG_DIR", "~/.config/mpkg")).expanduser()
_log_file = _log_dir / "failed.log"


def log_failure(canonical: str, reason: str) -> None:
    _log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with open(_log_file, "a") as f:
        f.write(f"{ts}  {canonical}  {reason}\n")
