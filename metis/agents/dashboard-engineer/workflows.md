# Dashboard Engineer Workflows

## 1. Stack-selection workflow

For each dashboard or app request:

1. identify the purpose
2. identify the data and interactions required
3. estimate complexity
4. decide whether:
   - a simple dashboard is enough
   - a modular app is needed
5. choose the stack

Typical options:

- R Shiny for analytics-heavy dashboards and close integration with R workflows
- a broader web stack when the system becomes a larger multi-page application

## 2. Shiny-architecture workflow

When R Shiny is appropriate:

1. decide if a simple app or modular architecture is needed
2. separate:
   - data logic
   - reactive logic
   - presentation logic
3. plan for maintainability
4. avoid dumping everything into one `app.R` if the app is central or growing

## 3. Command-center integration workflow

The command center should not be separate from the rest of the system.

The app should support:

- Control Room as home
- Library page
- PhD page
- Projects page
- Meetings page
- Ideas page
- possible specialist pages later

The command center should act as the overview and routing layer.

## 4. Visualization workflow

When designing visualizations:

1. clarify the question the chart should answer
2. choose the simplest chart that answers it well
3. maintain visual hierarchy
4. avoid clutter and decorative complexity

## 5. Implementation workflow

For a real dashboard build:

1. define the page structure
2. define reusable components
3. define data sources
4. define state and navigation
5. implement incrementally

## 6. Simple-vs-complex decision rule

Use a simple dashboard when:

- there are few views
- interactions are limited
- the dashboard is mostly analytical and self-contained

Use a more structured application when:

- multiple pages are needed
- several system functions must be combined
- the dashboard is becoming the daily control surface
- multiple data domains are linked
