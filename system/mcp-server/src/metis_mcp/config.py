"""Path resolution and environment variable handling for the Metis Research Cortex (RC)."""

import os
from pathlib import Path


def _infer_root() -> Path:
    """Infer RC root from server location: repo root (5 levels up from src/metis_mcp/config.py)."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent


def get_root() -> Path:
    """Return the RC root directory, from METIS_RC_ROOT env var or inferred."""
    env = os.environ.get("METIS_RC_ROOT") or os.environ.get("METIS_PKM_ROOT")
    if env:
        return Path(env).resolve()
    return _infer_root()


class Paths:
    """Central path registry for the Metis Research Context."""

    def __init__(self, root: Path | None = None):
        self.root = root or get_root()
        self.agents = self.root / "agents"
        self.research = self.root / "knowledge" / "domains" / "research"
        self.domains = self.root / "knowledge" / "domains"
        self.projects_active = self.root / "projects" / "active"
        self.literature_metadata = (
            self.root
            / "inputs"
            / "literature"
            / "metadata"
        )
        self.library = self.root / "knowledge" / "library"
        self.reviews = self.root / "outputs" / "reviews"
        self.config = self.root / "system" / "config"
        self.db = (
            self.root
            / "system"
            / "app"
            / "data"
            / "metis.sqlite"
        )


# Singleton instance
paths = Paths()
