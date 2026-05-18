"""Singleton FastMCP application instance.

Kept in a separate module so that both server.py and the tool modules
can import `app` without triggering a circular import.
"""
from mcp.server.fastmcp import FastMCP

app = FastMCP("metis-rc")
