# Code Staging Area

This folder is the drop zone for R scripts and other code files that need review or analysis.

## How to use

1. **Copy** (do not move) the script you want reviewed from its original project folder into a subfolder here
2. Name the subfolder after the project: `hat-dashboard/`, `hat-clustering/`, `multilevel/`, etc.
3. Ask the software-engineer agent to review it
4. After the review is complete, **delete the copy** — the original lives in the project folder

## Why copy and not link?
OneDrive paths change, symlinks are fragile on Windows/WSL. A deliberate copy makes it explicit that this is a snapshot for review, not the live file.

## What goes here
- R scripts submitted for code review
- Python scripts for review
- Shiny modules under development
- Short snippets that need debugging help

## What does NOT go here
- Full project folders (too large, keep them in their original location)
- Data files (keep in original project)
- `.Rproj` files

## Original project locations
| Project | Path |
|---|---|
| HAT Dashboard | `C:\Users\sverschaeve\OneDrive - ITG\Documents\2. HAT disease\1. Epi Data\7. Dashboard` |
| HAT Clustering / Risk Mapping | `C:\Users\sverschaeve\OneDrive - ITG\Documents\2. HAT disease\1. Epi Data\4. Clustering` |
| Multilevel Analysis Course | `C:\Users\sverschaeve\OneDrive - ITG\Documents\9. Education\1. Multilevel Analysis` |
