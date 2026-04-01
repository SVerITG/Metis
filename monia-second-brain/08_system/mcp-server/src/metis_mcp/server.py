"""MCP server bootstrap, tool registration, and main entry point."""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("metis-pkm")

# Import tool modules -- each registers handlers via @app.tool()
from metis_mcp.tools import (  # noqa: E402, F401
    agents,
    literature,
    notes,
    phd,
    projects,
    reviews,
    tasks,
)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
