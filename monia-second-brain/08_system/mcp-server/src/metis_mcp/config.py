"""Path resolution and environment variable handling for the Metis PKM."""

import os
from pathlib import Path


def _infer_root() -> Path:
    """Infer PKM root from server location: ../../.. from src/metis_mcp/config.py."""
    return Path(__file__).resolve().parent.parent.parent.parent


def get_root() -> Path:
    """Return the PKM root directory, from METIS_PKM_ROOT env var or inferred."""
    env = os.environ.get("METIS_PKM_ROOT")
    if env:
        return Path(env).resolve()
    return _infer_root()


class Paths:
    """Central path registry for the Metis PKM."""

    def __init__(self, root: Path | None = None):
        self.root = root or get_root()
        self.agents = self.root / "02_agents"
        self.phd = self.root / "03_domains" / "phd"
        self.domains = self.root / "03_domains"
        self.projects_active = self.root / "04_projects" / "active"
        self.literature_metadata = (
            self.root
            / "05_sources"
            / "literature"
            / "sleeping-sickness"
            / "metadata"
        )
        self.library = self.root / "06_library"
        self.reviews = self.root / "07_outputs" / "reviews"
        self.db = (
            self.root
            / "07_outputs"
            / "apps"
            / "metis-dashboard"
            / "data"
            / "metis.sqlite"
        )


# Singleton instance
paths = Paths()
