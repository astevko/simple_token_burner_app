"""Load ``.env`` and read burner configuration from the environment."""

import os
from pathlib import Path
from typing import Optional


def load_dotenv_file() -> None:
    """Load a ``.env`` file from the project directory if present.

    Existing environment variables are not overwritten (CLI flags and exports
    take precedence when set before launch).
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    # Project root: parent of this package directory.
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env", override=False)


def getenv_str(name: str, default: Optional[str] = None) -> Optional[str]:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return raw.strip()

def getenv_int(name: str, default: Optional[int] = None) -> Optional[int]:
    """Parse an integer environment variable, returning *default* if unset."""
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return int(raw)
