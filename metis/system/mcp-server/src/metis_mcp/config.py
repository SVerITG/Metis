"""Path resolution and environment variable handling for the Metis Research Cortex (RC)."""

import os
from pathlib import Path


def _infer_root() -> Path:
    """Infer RC root from server location: metis/ (5 levels up from src/metis_mcp/config.py)."""
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
        self.agents = self.root / "02_agents"
        self.research = self.root / "03_domains" / "research"
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
