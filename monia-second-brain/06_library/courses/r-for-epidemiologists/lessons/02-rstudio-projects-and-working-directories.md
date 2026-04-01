# RStudio, Projects, and Working Directories

## Learning objectives
- Set up RStudio projects for stable file paths.
- Explain why working-directory discipline matters.
- Recognize common setup mistakes that break reproducibility.

## Prerequisites
- Why R for epidemiology.

## Content
RStudio projects help analysts keep code, data, and outputs organized around a single working folder. That reduces brittle file paths and makes collaboration easier. Good project structure is an early payoff in R: raw data, scripts, outputs, and reports should be separated clearly.

Hardcoded absolute paths are a common beginner mistake. So is running scripts from inconsistent directories. Projects solve much of this by creating a stable context for relative paths and keeping analysis self-contained.

## Key takeaways
- Projects improve organization and portability.
- Relative paths are more reproducible than machine-specific absolute paths.
- Early setup discipline prevents later workflow pain.

## Self-check questions
1. Why are absolute paths risky?
2. What does an RStudio project help stabilize?
3. Why should outputs and raw data be separated?
4. What is one common working-directory mistake?
5. Why does this matter for collaboration?

## Answer key
1. Because they often break on another machine or folder structure.
2. File organization and relative path use.
3. To protect raw data and keep workflows clearer.
4. Running scripts from inconsistent folders.
5. Shared projects are easier for others to run and understand.

## Further reading
- [Posit documentation](https://posit.co/)
- [R for Data Science](https://r4ds.hadley.nz/)

## Links to Metis library
- `06_library/methods/data-management.md`
- `06_library/methods/writing-for-journals.md`
