# Dashboard Engineer Workflows

The Metis dashboard is a **FastAPI + HTMX + Jinja2** application in `system/app-py/`
(no JS framework, no R Shiny). All workflows below target that stack.

## 1. Change-scoping workflow

For each dashboard request:

1. identify the purpose — what decision does this view support?
2. identify the data and interactions required (db.py query, MCP tool, or external API)
3. locate the touchpoints:
   - which router (`routers/<tab>.py`)
   - which template/partial (`templates/`, `templates/partials/`)
   - which HTMX endpoint serves the fragment
4. estimate complexity — a single partial, or a small set of composed partials?
5. confirm the change doesn't break an existing `hx-target`/`hx-swap` contract or a partial reused by other views

## 2. Endpoint + partial workflow

When building or fixing a view:

1. add/modify the endpoint in the correct router; return `templates.TemplateResponse(request, "partials/<name>.html", {...})` as an `HTMLResponse`
2. keep the partial self-contained (no full `<html>` wrapper)
3. wire it into the parent tab template with `hx-get` + an appropriate `hx-trigger`
4. add a skeleton loader for partials that hit the DB or an MCP tool
5. separate concerns: data logic in `db.py`/tools, presentation in the template, glue in the router

## 3. Tab integration workflow

The dashboard tabs form one coherent surface. Current tabs:

- Today (home / morning brief), Knowledge, Meetings, Learning, Work,
  Thinking, Planner, Teach, Metis

New views should slot into the right existing tab rather than spawning detached pages.
Changing the tab structure itself requires approval (see contract / registry).

## 4. Visualization workflow

When designing visualizations:

1. clarify the question the chart should answer
2. choose the simplest form that answers it well — HTML/CSS first; Chart.js when interactivity or axis precision is needed; Leaflet for geographic data; SVG sparklines for compact in-card trends
3. maintain visual hierarchy; use the `--m-*` CSS tokens, never hardcoded colours
4. avoid clutter and decorative complexity

## 5. Implementation workflow

For a real dashboard build:

1. define the view structure (which partials compose it)
2. define reusable components / shared CSS classes
3. define data sources (db.py queries / MCP tools)
4. define endpoints, HTMX triggers, and state
5. implement incrementally; restart with `system/app-py/run.sh` and verify in the browser

## 6. Simple-vs-richer decision rule

Use a single partial when:

- the view is one self-contained panel
- interactions are limited to a refresh or a simple swap

Compose multiple partials / add helpers when:

- the view aggregates several data domains
- parts refresh independently via different HTMX triggers
- a router is growing unwieldy (today.py / knowledge.py are already large — extract partials/helpers rather than piling on)
