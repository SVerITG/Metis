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
| [Your Project] | `C:\\Users\\{username}\\[path-to-project]`
| [Your Dataset Analysis] | `C:\\Users\\{username}\\[path-to-analysis]`
| [Your Course] | `C:\\Users\\{username}\\[path-to-course]`
