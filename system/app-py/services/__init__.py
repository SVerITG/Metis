"""Service modules for the dashboard — logic that is not a route.

Kept out of routers/ deliberately: `acquire.py` is called from a route, from the
scheduler, and (once reinstalled) from an MCP tool. A module three callers share
does not belong inside any one of their files.
"""
