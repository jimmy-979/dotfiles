import os
from pathlib import Path
from typing import Any

import tomllib

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "packages.toml"


def load_manifest() -> dict[str, Any]:
    if not MANIFEST.exists():
        raise RuntimeError(f"Package manifest not found: {MANIFEST}")
    with MANIFEST.open("rb") as f:
        return tomllib.load(f)


def expand_path(path: str | Path) -> Path:
    return Path(os.path.expandvars(str(path))).expanduser()


def config_source_path(source: str) -> Path:
    path = expand_path(source)
    return path if path.is_absolute() else ROOT / path
