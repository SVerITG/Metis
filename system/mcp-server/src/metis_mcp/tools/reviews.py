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
    """Save an agent's output as a review file and record the run.

    This is the standard way a Metis agent persists its work: it writes the
    markdown to outputs/reviews/{agent_slug}/{date}_{task_slug}.md and, by
    default, logs the run so the dashboard's Agents tab tracks it. Use it at the
    end of any substantive agent task so the result is filed and discoverable.

    Args:
        agent_slug: Slug of the agent that produced the review
            (e.g. "epidemiologist", "writing-partner").
        task_slug: Short kebab-case slug identifying the task; becomes part of
            the filename (e.g. "article1-methodology").
        content: The full review content as markdown.
        log_run: Whether to also record this as an agent run for the dashboard.
            Defaults to True.

    Returns:
        A confirmation with the path of the saved review file.
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
