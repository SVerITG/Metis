"""Singleton FastMCP application instance.

Kept in a separate module so that both server.py and the tool modules
can import `app` without triggering a circular import.
"""
from mcp.server.fastmcp import FastMCP

app = FastMCP(
    "metis-rc",
    instructions=(
        "Metis is a research companion for Claude that keeps your data on your machine. "
        "It gives Claude a persistent "
        "memory of your field, your papers, and your working history, and routes each "
        "request to one of 30+ specialist skills — Librarian, Methods Coach, Writing "
        "Partner, Meeting Memory, Epidemiologist, Course Builder, and more. Knowledge "
        "answers are cited from the researcher's own indexed library, never invented. "
        "Everything you capture — papers, meeting transcripts, ideas, notes, journal "
        "entries and tasks — is automatically cross-pollinated, so related work surfaces "
        "across time without you searching for it. Each week Metis also reviews its own "
        "performance and drafts behaviour improvements for your approval. "
        "Your documents, notes, embeddings and memory stay on your machine; reasoning "
        "runs on the Claude API."
    ),
    website_url="https://github.com/SVerITG/Metis_PH",
)
