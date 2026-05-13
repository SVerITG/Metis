# GIS Basics and Coordinate Systems

## Learning objectives
- Distinguish vector and raster spatial data and know when each is useful.
- Explain coordinate reference systems and why projection choices matter.
- Recognize common GIS errors involving reprojection, spatial joins, and misaligned layers.
- Apply a basic workflow for handling spatial data safely before analysis.

## Prerequisites
- Why space matters.

## Content

### Section 1: What GIS contributes to epidemiology
Geographic information systems, or GIS, help epidemiologists store, inspect, link, and analyze spatial data. In practice, GIS work often begins before any formal spatial statistic is calculated. It involves locating facilities, linking case data to boundaries, checking whether layers align, and preparing data for mapping or modeling.

This matters because many spatial errors are not advanced modeling problems. They are data-handling problems: wrong coordinates, missing projection metadata, inconsistent boundary codes, or layers that appear aligned visually but are not truly aligned mathematically.

### Section 2: Vector and raster data
Spatial data come in two broad forms.

**Vector data** represent discrete objects:

- points for cases, facilities, or households
- lines for roads, rivers, or travel routes
- polygons for districts, health zones, or catchment areas

**Raster data** represent gridded surfaces:

- rainfall
- temperature
- elevation
- land cover
- modeled suitability surfaces

The distinction matters because these data types answer different questions. Vector data are useful for boundaries and discrete locations. Raster data are useful for continuous environmental variation.

### Section 3: Coordinate reference systems
A **coordinate reference system (CRS)** tells the software how coordinates relate to locations on the earth.

A common geographic CRS is **WGS84**, which stores latitude and longitude in degrees. This is useful for GPS collection and global storage.

A **projected CRS** transforms the earth's surface into a flat coordinate system, usually in meters. Projected systems are often better for:

- measuring distance
- buffering
- calculating area
- local spatial analysis

The key practical rule is simple: always inspect the CRS of every layer before combining datasets.

### Section 4: Why projections matter
Latitude-longitude coordinates are not ideal for all tasks. Degrees are not constant distance units, so using raw geographic coordinates for distance-based analysis can produce wrong answers.

For example, if you want to estimate travel distance to a facility, create a 5 km buffer, or calculate the area of a polygon, a suitable projected CRS is usually preferable.

A common beginner mistake is to run a buffer or nearest-neighbor calculation in degrees and assume the result is in meters. It is not.

### Section 5: Worked example - failed point-in-polygon join
Imagine you have:

- village points collected by GPS in WGS84
- health-zone polygons stored in a projected CRS

If you try a spatial join without reconciling CRS, several things can go wrong:

- the join may fail
- the points may appear far away from the polygons
- the software may silently reproject or mis-handle the layers
- villages may be assigned to the wrong health zone

This is not a minor technical issue. A single CRS mistake can invalidate later disease maps, facility-access analyses, and cluster detection.

### Section 6: Reprojection and metadata discipline
When layers use different CRSs, they often need to be reprojected to a common system before analysis. In R, this is commonly done with tools such as `st_transform()` for vector data.

But reprojection only works properly if the original CRS metadata are correct. If a layer has the wrong CRS assigned, simply transforming it can make the error worse.

That is why GIS work requires metadata discipline:

- know the original coordinate system
- document reprojection steps
- inspect layer alignment after transformation
- avoid guessing when metadata are missing

### Section 7: Common GIS joins in epidemiology
Two join types are especially common.

**Attribute joins** connect tables through shared codes such as district IDs or facility identifiers.

**Spatial joins** connect data based on location, such as assigning villages to health zones or linking case points to raster covariates.

Both are vulnerable to error. Attribute joins can fail because of naming inconsistencies or boundary changes over time. Spatial joins can fail because of CRS mismatch, bad geometries, or ambiguous location accuracy.

### Section 8: Practical workflow habits
A safe GIS workflow in epidemiology often looks like this:

1. inspect file format and geometry type
2. inspect CRS for every layer
3. verify identifiers and metadata
4. reproject layers when necessary
5. plot layers together to confirm alignment
6. only then begin joins, buffers, or modeling

These checks can feel slow, but they save time by preventing silent errors later.

### Section 9: Common mistakes
Several GIS mistakes recur often.

- mixing layers with different CRSs
- buffering in degrees instead of meters
- treating raster and vector data as interchangeable
- assuming shapefile metadata are complete and reliable
- failing to check whether points fall inside plausible boundaries

The practical lesson is that GIS quality control is part of epidemiologic validity, not a purely technical pre-processing step.

## Key takeaways
- GIS work in epidemiology starts with reliable spatial data handling, not only advanced modeling.
- Vector data represent discrete objects; raster data represent continuous surfaces.
- Coordinate reference systems determine how spatial coordinates are interpreted and whether distance or area calculations make sense.
- Reprojection and spatial joins require explicit checking, because silent alignment errors are common.
- A disciplined GIS workflow prevents downstream mapping and modeling errors.

## Self-check questions
1. What is the difference between vector and raster data?
2. Why is CRS checking an early workflow step rather than a later one?
3. Why can latitude-longitude be a poor choice for distance calculations?
4. What can go wrong in a point-in-polygon join if the layers use different CRSs?
5. Why are attribute joins vulnerable even when no map geometry is involved?
6. What is one basic GIS quality-control step you should always do before analysis?

## Answer key
1. Vector data store discrete points, lines, and polygons, while raster data store gridded continuous surfaces.
2. Because CRS mismatch can invalidate joins, distances, buffers, and map alignment from the start.
3. Because degrees are angular units, not constant-distance units like meters.
4. Points may fail to join, align incorrectly, or be assigned to the wrong area because the coordinate systems are incompatible.
5. Because identifier fields may differ across sources due to spelling changes, coding inconsistencies, or boundary revisions.
6. Examples include checking CRS, plotting layers together, verifying point locations fall in plausible areas, or confirming join keys.

## Further reading
- [Simple Features for R](https://r-spatial.github.io/sf/)
- [CRAN terra package](https://cran.r-project.org/package=terra)
- [R-spatial transition guidance](https://r-spatial.org/r/2023/05/15/evolution4.html)

## Links to Metis library
- `knowledge/library/methods/gis-for-epidemiology.md`
- `knowledge/library/methods/data-management.md`
- `knowledge/library/methods/spatial-epidemiology.md`
