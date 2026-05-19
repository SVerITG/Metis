# News Radar — Monitored Sources

Replace this file with your domain-specific news sources.
Configure via the config wizard (`/metis-config news`) or edit directly.

## Structure

```yaml
rss_feeds:
  - url: https://example.com/feed.rss
    name: Source Name
    domain: your-topic

pubmed_queries:
  - query: "your mesh terms AND surveillance"
    label: Your Topic Alerts

openalex_queries:
  - query: your research topics
    label: Literature Alerts
```

In a domain edition (e.g. Metis_PH), this file contains pre-configured feeds
for that field. Add yours after running the config wizard.
