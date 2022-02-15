---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.11.5
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Rural, Ag and Food Industries, NETS in ADRF

## Research principles
- reproducible
- literate programming
  - code + doc + output + thought process
  - notebooks
- modular: composable and reusable
- scalable
  - compute: bigger data, longer computation
  - collaboration: bigger team, different programming languages
  
## Tools
- Jupyter notebooks
  - language agnostic (?)
- git
  - value added must outweigh learning cost
  - `nbconvert` to clear nbs
  - `nbdime` to diff and merge
- `nbdev` or some reduced form
  - notebook is single source
  - build modules and docs from nbs
- widgets, Voilà dashboards

## rurec
- https://github.com/antonbabkin/rurec
- prototype built from InfoGroup
- components:
  - prepare source data: InfoGroup, geo, NAICS, ERS rurality codes...
  - define and compute outputs
  - benchmark against CBP/BDS
  - present outputs
    - static tables and graphs
    - live dashboards
- ran into scaling problems, took step back to re-design, ran out of time
