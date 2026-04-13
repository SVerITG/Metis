"""Save review outputs and optionally log the agent run."""

import datetime

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.tools.agents import log_agent_run
from metis_mcp.app_instance import app


@app.tool()
async def save_review(
    agent_slug: str,
    task_slug: str,
    content: str,
    log_run: bool = True,
) -> list[TextContent]:
    """Save a review document to the PKM and optionally log the agent run.

    Writes to 07_outputs/reviews/{agent_slug}/{date}_{task_slug}.md.

    Args:
        agent_slug: The agent that produced the review.
        task_slug: Short slug identifying the review task.
        content: The full review content in markdown.
        log_run: Whether to also log this as an agent run (default True).
    """
    today = datetime.date.today().isoformat()
    review_dir = paths.reviews / agent_slug
    filename = f"{today}_{task_slug}.md"
    filepath = review_dir / filename

    try:
        review_dir.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
    except Exception as e:
        return [TextContent(type="text", text=f"Error writing review: {e}")]

    result_text = f"Review saved: {filepath.relative_to(paths.root)}"

    if log_run:
        log_result = await log_agent_run(
            agent_slug=agent_slug,
            task_summary=f"Review: {task_slug}",
            output_path=str(filepath),
        )
        if log_result:
            result_text += f"\n{log_result[0].text}"

    return [TextContent(type="text", text=result_text)]
