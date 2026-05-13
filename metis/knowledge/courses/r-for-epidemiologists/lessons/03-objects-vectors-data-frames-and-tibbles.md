# Objects, Vectors, Data Frames, and Tibbles

## Learning objectives
- Describe core R objects used in routine analysis.
- Explain the difference between vectors and tabular objects.
- Recognize why tibble-like tables are useful in modern workflows.

## Prerequisites
- RStudio projects and working directories.

## Content
R stores information in objects. Analysts work most often with vectors, lists, and data frames. A vector is a single typed collection, such as numeric ages or character district names. A data frame is a table where each column is a vector of equal length.

Tibbles are a modern, easier-to-read data-frame variant used heavily in tidyverse workflows. Understanding these structures matters because many beginner errors come from not knowing what type of object a function expects or returns.

## Key takeaways
- Vectors are single typed collections; data frames are tables.
- Many R errors are object-type misunderstandings.
- Tibbles improve readability in modern workflows.

## Self-check questions
1. What is a vector?
2. What is a data frame?
3. Why do object types matter in R?
4. What is one advantage of tibbles?
5. What kind of mistake can happen if object type is misunderstood?

## Answer key
1. A one-dimensional typed collection of values.
2. A tabular object made of equal-length columns.
3. Because functions behave differently depending on input structure.
4. Cleaner printing and modern tidyverse compatibility.
5. Applying the wrong function or misreading the output structure.

## Further reading
- [R for Data Science](https://r4ds.hadley.nz/)
- [Posit Cheatsheets](https://posit.co/resources/cheatsheets/)

## Links to Metis library
- `knowledge/library/methods/data-management.md`
