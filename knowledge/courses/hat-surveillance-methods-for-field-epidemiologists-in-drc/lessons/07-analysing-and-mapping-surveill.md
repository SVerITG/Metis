# Lesson 7 — Analysing and Mapping Surveillance Data in R

## Learning objectives
By the end of this lesson you will be able to:
- **Compute** health-zone gHAT incidence per 10,000 population using R (tidyverse).
- **Produce** a time trend of cases by year for a focus.
- **Analyse** the spatial pattern of cases with a simple choropleth and interpret it for the elimination threshold.

## Prerequisites
- Lessons 4 and 5 (case definitions, incidence denominators, the case-based data the Atlas holds).
- Basic R: installing/loading packages, reading a CSV, running a script top to bottom.

## Content

### Section 1: The data we analyse
For surveillance analysis you typically have a tidy table of **cases by health zone by year**, plus a **population** denominator per zone, plus (for mapping) a **spatial boundaries** file. We will use small, illustrative tables you could type by hand so the code runs anywhere with a standard tidyverse install.

The elimination indicator we keep returning to is **cases per 10,000 population per year per focus** — so the central computation is an incidence rate, and the central comparison is against the threshold of 1 per 10,000.

### Section 2: Computing incidence per 10,000
```r
library(tidyverse)

# Illustrative case + population data for four DRC health zones, one year
hz <- tibble(
  health_zone = c("Yasa Bonga", "Mosango", "Bagata", "Bulungu"),
  cases       = c(3, 0, 7, 1),
  population  = c(145000, 98000, 120000, 210000)
)

hz <- hz |>
  mutate(
    incidence_per_10k = cases / population * 10000,
    above_threshold   = incidence_per_10k >= 1
  )

hz
#> # A tibble: 4 x 4
#>   health_zone cases population incidence_per_10k above_threshold
#>   <chr>       <dbl>      <dbl>             <dbl> <lgl>
#> 1 Yasa Bonga      3     145000             0.207 FALSE
#> 2 Mosango         0      98000             0     FALSE
#> 3 Bagata          7     120000             0.583 FALSE
#> 4 Bulungu         1     210000             0.0476 FALSE
```

All four zones sit below the 1-per-10,000 EPHP threshold — but note Bagata's 7 cases. A low *rate* in a large population can still mean an active micro-focus, which is why Lesson 8 looks at sub-zone geography, not just the zonal rate.

### Section 3: A time trend for a focus
```r
library(tidyverse)

trend <- tibble(
  year  = 2016:2024,
  cases = c(58, 41, 33, 22, 17, 11, 8, 5, 3)
)

ggplot(trend, aes(x = year, y = cases)) +
  geom_line() +
  geom_point() +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "gHAT cases in an illustrative DRC focus, 2016-2024",
    x = "Year", y = "Confirmed cases"
  ) +
  theme_minimal()
# Expected output: a downward line from 58 (2016) to 3 (2024),
# showing sustained decline consistent with progress toward elimination.
```

A declining trend is encouraging, but recall Lesson 3: only trust it if screening coverage held up over the same years. Always plot the trend beside the coverage history.

### Section 4: A simple choropleth
A choropleth shades each zone by its incidence. With real data you would join an `sf` boundaries object; here is the pattern using the incidence table from Section 2.

```r
library(tidyverse)
library(sf)   # spatial data frames

# In practice: read real boundaries, e.g.
# zones_sf <- st_read("drc_health_zones.gpkg")
# For a runnable illustration, attach incidence to a placeholder geometry join:
zones_sf <- st_read(system.file("shape/nc.shp", package = "sf")) |>  # stand-in polygons
  slice(1:4) |>
  mutate(health_zone = hz$health_zone) |>
  left_join(hz, by = "health_zone")

ggplot(zones_sf) +
  geom_sf(aes(fill = incidence_per_10k)) +
  scale_fill_viridis_c(name = "Cases /10k") +
  labs(title = "gHAT incidence by health zone (illustrative geometry)") +
  theme_void()
# Expected output: four polygons shaded by incidence; the polygon mapped
# to "Bagata" is the darkest, flagging it for sub-zone investigation.
```

Note: `nc.shp` ships with the `sf` package, so this block runs on a standard install. Swap in real DRC health-zone boundaries when you have them. The point of the map is to make a high-incidence zone *visible* so you target it.

### Section 5: From map to action
The analysis loop closes back onto the field: a zone or sub-zone that lights up gets a reactive screening round (Lesson 3) and, if riverine, a tiny-target review (Lesson 6); a zone with zero cases but poor coverage gets a coverage fix before you believe its zero. Analysis is not the end of surveillance — it is how you decide where to send the next team.

## Summary
- Incidence per 10,000 is computed as cases / population × 10,000 and compared against the EPHP threshold of 1 per 10,000.
- A low zonal rate can still hide an active micro-focus, so pair rates with case counts and sub-zone geography.
- Time trends and choropleths (tidyverse + ggplot2/sf) turn surveillance tables into targeting decisions.
- Always read trends and maps alongside screening coverage before drawing reassuring conclusions.

## Exercises
1. Extend the `hz` table with a fifth zone (cases = 12, population = 60,000). Compute its incidence per 10,000 and state whether it crosses the EPHP threshold.
2. Modify the time-trend code to plot cases *and* an overlaid screening-coverage series (invent coverage values). Why does the second series change how you read the first?
3. You produce a choropleth where one zone is dark (high incidence) but its total case count is 2. Write two sentences on whether this is an alarm or an artefact, and what you would check next.

## Further reading
- Wickham H, Grolemund G. *R for Data Science* (2e, free online) — tidyverse foundations.
- Lovelace R et al. *Geocomputation with R* (free online) — `sf` and choropleths.
- Franco JR et al. *Monitoring the elimination of HAT...* PLoS Negl Trop Dis, 2020 — for the focus-level rate logic.
