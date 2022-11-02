---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.0
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

```{raw-cell}
:tags: []

---
title: "Stata + Python"
format:
  html: 
    code-fold: true
    ipynb-filters:
      - reseng/nbd.py filter-docs
---
```

+++ {"tags": ["nbd-docs"]}

Beginning with version 17, Stata API can now be directly called from Python code. This notebook is an example of a start to finish analysis the combines stronger parts of Python and Stata. Specifically, I look how fraction of food and agricultural industries (FAI) employment relates to proportion of population living in rural areas.

- Download and parse raw data from web (Python).
- Compute new variables, merge two tables into single dataset (Python).
- Run an OLS regression and predict marginal effects (Stata).
- Display estimation results in a notebook and allow dynamic re-estimation controlled by widgets (Python).

Guides and examples can be found at official **pystata** package [documentation](https://www.stata.com/python/pystata/index.html).

# Installation

In order to run this example notebook, you need Stata 17 installation and a Python environment with `jupyter`, `pandas`, `matplotlib` and `ipywidgets` packages.

+++ {"tags": ["nbd-docs"]}

# Configuration

Add location of **pystata** to paths that Python searches for import.

```{code-cell} ipython3
:tags: [nbd-docs]

import sys
sys.path.append('/usr/local/stata17/utilities')
import pystata
pystata.config.init('se')
```

+++ {"tags": ["nbd-docs"]}

# Prepare data with Python

## Download NAICS codes and pick a subset

NAICS classification used in [2012 CBP](https://www.census.gov/data/datasets/2012/econ/cbp/2012-cbp.html).

Pick 6-digit NAICS codes that have "agri", "food" or "farm" in description.

```{code-cell} ipython3
:tags: [nbd-docs]

import pandas as pd

df = pd.read_csv('https://www2.census.gov/programs-surveys/cbp/technical-documentation/reference/naics-descriptions/naics2012.txt')
df = df[~df['NAICS'].str[-1].isin(['-', '/'])]
naics_fai = df.loc[[any(x in y.lower() for x in ('agri', 'food', 'farm')) for y in df['DESCRIPTION']], 'NAICS'].tolist()
df.query('NAICS.isin(@naics_fai)')
```

+++ {"tags": ["nbd-docs"]}

## Download CBP and compute FAI employment share

Using county-industry employment in 2012.

```{code-cell} ipython3
:tags: [nbd-docs]

df = pd.read_csv('https://www2.census.gov/programs-surveys/cbp/datasets/2012/cbp12co.zip', dtype=str)
df = df[['fipstate', 'fipscty', 'naics', 'emp']]
df['emp'] = df['emp'].astype(int)
df['stcty'] = df['fipstate'] + df['fipscty']
df.loc[df['naics'] == '------', 'ind'] = 'all'
df.loc[df['naics'].isin(naics_fai), 'ind'] = 'fai'
d = df.groupby(['stcty', 'ind'])['emp'].sum().unstack().fillna(0)
fai_share = d['fai'] / d['all']
fai_share.describe([0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1])
```

+++ {"tags": ["nbd-docs"]}

## Download and compute rural population shares

County rurality is computed as fraction of population living in rural tracts. Tracts are defined as rural if their ERS [RUCA codes](https://www.ers.usda.gov/data-products/rural-urban-commuting-area-codes/documentation/) are "6", "9" or "10".

```{code-cell} ipython3
:tags: [nbd-docs]

df = pd.read_excel('https://www.ers.usda.gov/webdocs/DataFiles/53241/ruca2010revised.xlsx?v=2541.2', dtype=str, skiprows=1)
df = df[['State-County FIPS Code', 'Primary RUCA Code 2010', 'Secondary RUCA Code, 2010 (see errata)', 'Tract Population, 2010']]
df.columns = ['stcty', 'ruca_p', 'ruca_s', 'pop']
df['pop'] = df['pop'].astype(int)
df['rural'] = df['ruca_p'].isin(['6', '9', '10'])
d = df.groupby(['stcty', 'rural'])['pop'].sum().unstack().fillna(0)
rural_pop_share = d[True] / d.sum(1)
rural_pop_share.describe([0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1])
```

+++ {"tags": ["nbd-docs"]}

## Merge employment and population data

```{code-cell} ipython3
:tags: [nbd-docs]

df = pd.concat([rural_pop_share, fai_share], 1)
df.columns = ['rural_pop_share', 'fai_share']
df = df.dropna()
reg_df = df
df.sample(frac=0.1).plot.scatter('rural_pop_share', 'fai_share')
```

+++ {"tags": ["nbd-docs"]}

# Analyze with Stata, report with Python

## IPython magics

IPython magic `%%stata` can be used to execute snippets of Stata code. Here we use it to load previously prepared Pandas DataFrame as an active Stata dataset with a `-d` parameter (`-force` to replace previously loaded dataset).

```{code-cell} ipython3
:tags: [nbd-docs]

%%stata -force -d reg_df
describe, short
```

+++ {"tags": ["nbd-docs"]}

We can use the same approach to run regression and post-estimation of marginal effects, printing output logs in the notebook. Estimation results can be brought back to Python context with `-ret`, `-eret` and `-sret`.

```{code-cell} ipython3
:tags: [nbd-docs]

%%stata -ret reg_ret
reg fai_share rural_pop_share
margins, at(rural_pop_share=(0(0.1)1)) level(95)
```

+++ {"tags": ["nbd-docs"]}

All **r()** returns from the `margins` command are now stored in a Python dict.

```{code-cell} ipython3
:tags: [nbd-docs]

reg_ret
```

+++ {"tags": ["nbd-docs"]}

Stata plots will also be displayed in the notebook.

```{code-cell} ipython3
:tags: [nbd-docs]

%%stata
twoway scatter fai_share rural_pop_share in 1/500
```

+++ {"tags": ["nbd-docs"]}

## Stata API

We can also use `pystata.stata.run()` function to submit a string of Stata code for execution and retrieve returns with `pystata.stata.get_return()`. This allows for a more flexible customization of commands with Python string manipulation tools. Here we wrap regression and marginal effects code in a Python function that can be used to run estimation with different parameters and plot results.

```{code-cell} ipython3
:tags: [nbd-docs]

from pystata import stata
import matplotlib.pyplot as plt

def reg_margin_plot(level=95, poly=1):
    rhs = 'rural_pop_share' + (poly-1) * ' c.rural_pop_share#c.rural_pop_share'
    stata.run(f'''
    reg fai_share {rhs}
    margins, at(rural_pop_share=(0(0.1)1)) level({level})
    ''', quietly=True)

    r = stata.get_return()
    plt.plot(r['r(at)'], r['r(b)'].T, 'b-')
    plt.plot(r['r(at)'], r['r(table)'][4, :], 'b:')
    plt.plot(r['r(at)'], r['r(table)'][5, :], 'b:')
    plt.xlabel('Rural population share')
    plt.ylabel('FAI employment share')
    f = plt.gcf()
    plt.close()
    return f

reg_margin_plot(90, 2)
```

+++ {"tags": ["nbd-docs"]}

Now we can easily create an interactive interface to the regression code using widgets.

```{code-cell} ipython3
:tags: [nbd-docs]

import ipywidgets as widgets
widgets.interact(reg_margin_plot,
                 level=widgets.IntSlider(min=80, max=99, step=1, value=95, description='CI %'),
                 poly=widgets.RadioButtons(options=[('Linear', 1), ('Quadratic', 2), ('Cubic', 3)], value=1, description='Polynomial'))
```
