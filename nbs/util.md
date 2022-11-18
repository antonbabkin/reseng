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
title: "Misc utils"
format:
  html: 
    code-fold: true
    ipynb-filters:
      - reseng/nbd.py filter-docs
---
```

+++ {"tags": ["nbd-docs"]}

This module includes various useful utilities.

```{code-cell} ipython3
:tags: [nbd-module]

import shutil
import urllib
from pathlib import Path
from urllib.parse import urlparse, unquote
import tempfile

import requests
import numpy as np
import pandas as pd
```

+++ {"tags": ["nbd-docs"]}

# File download

`download_file()` downloads a file and returns it's path.

```{code-cell} ipython3
:tags: [nbd-module]

def download_file(url, dir=None, fname=None, overwrite=False):
    """Download file from given `url` and put it into `dir`.
    Current working directory is used as default. Missing directories are created.
    File name from `url` is used as default.
    Return absolute pathlib.Path of the downloaded file.
    Supports HTTP and FTP protocols.
    """
    
    if dir is None:
        dir = '.'
    dpath = Path(dir).resolve()
    dpath.mkdir(parents=True, exist_ok=True)

    if fname is None:
        fname = unquote(Path(urlparse(url).path).name)
    fpath = dpath / fname
    
    if not overwrite and fpath.exists():
        print(f'File {fname} already exists.')
        return fpath

    if urlparse(url).scheme == 'ftp':
        with urllib.request.urlopen(url) as r:
            with open(fpath, 'wb') as f:
                shutil.copyfileobj(r, f)
    else:
        with requests.get(url) as r:
            r.raise_for_status()
            with open(fpath, 'wb') as f:
                f.write(r.content)
    
    print(f'Downloaded file "{fname}".')
    return fpath 


def test_download_file():
    with tempfile.TemporaryDirectory() as temp_dir:
        print('Testing FTP download')
        f = download_file('ftp://ftp.nass.usda.gov/quickstats/qs.sample.txt', temp_dir)
        assert len(f.open().read()) == 22891    
    
        print('Testing HTTP download')
        from reseng.nbd import Nbd
        nbd = Nbd('reseng')
        cloned_file = nbd.root / 'LICENSE'
        
        downloaded_file = download_file('https://raw.githubusercontent.com/antonbabkin/reseng/master/LICENSE', temp_dir)
        assert cloned_file.open().read() == downloaded_file.open().read()
```

```{code-cell} ipython3
:tags: []

test_download_file()
```

+++ {"tags": ["nbd-docs"]}

# Pandas extensions

`tag_invalid_values()` takes a `pandas.Series` and contraints like `non-missing` or `> 5`, and reports which values do not satisfy the contraints.

```{code-cell} ipython3
:tags: [nbd-module]

def tag_invalid_values(ser, notna=False, unique=False, nchar=None, number=False, cats=None,
                 eq=None, gt=None, ge=None, lt=None, le=None):
    """Return array with indicators of invalid values in `ser`.

    Validity checks are performed against flags given as keyword arguments.
    If multiple flags are present, value is only valid if it satisfies all of them.
    
    If a value is missing, it will be marked invalid by `notna` flag.
    IMPORTANT: missing values will NOT be flagged invalid by any other flags.
    
    `unique` will tag all duplicates as invalid.
    """
    # idea: print warning if unsupported values are present, e.g. str values with "ge" flag
    valid = np.ones_like(ser, bool)
    ser_isna = ser.isna()
    ser_notna = ~ser_isna
    
    if notna:
        valid &= ser_notna
        
    if unique:
        valid &= (ser_isna | ~ser.duplicated(False))
    
    if nchar is not None:
        valid &= (ser_isna | (ser.str.len() == nchar))
        
    if number:
        conversion_fail = ser_notna & pd.to_numeric(ser, 'coerce').isna()
        valid &= (ser_isna | ~conversion_fail)
        
    if cats is not None:
        valid &= (ser_isna | ser.isin(cats))
        
    if eq is not None:
        valid &= (ser_isna | (ser == eq))
    if gt is not None:
        valid &= (ser_isna | (ser > gt))
    if ge is not None:
        valid &= (ser_isna | (ser >= ge))
    if lt is not None:
        valid &= (ser_isna | (ser < lt))
    if le is not None:
        valid &= (ser_isna | (ser <= le))
        
    return ~valid.values
        

def validate_values(df, constraints):
    """Return list of invalid values in a dataframe.
    `constraints` should be a dictionary of column names and 
    their respective constraints as dict to be passed to validator function.
    """
    invalid_list = []
    for col, flags in constraints.items():
        inval_bool = tag_invalid_values(df[col], **flags)
        inval_row_idx, = inval_bool.nonzero()
        for i in inval_row_idx:
            invalid_list.append({'col': col, 'row': i, 'idx': df.index[i], 'val': df[col].iloc[i]})
            
    return invalid_list

def test_tag_invalid_values():
    s = pd.Series(['alpha', 'beta', 'beta', '0123', np.nan], dtype='str')
    assert (tag_invalid_values(s, notna=True) == [False, False, False, False, True]).all()
    assert (tag_invalid_values(s, unique=True) == [False, True, True, False, False]).all()
    assert (tag_invalid_values(s, nchar=4) == [True, False, False, False, False]).all()
    assert (tag_invalid_values(s, number=True) == [True, True, True, False, False]).all()
    assert (tag_invalid_values(s, cats=['alpha', 'beta']) == [False, False, False, True, False]).all()
    assert (tag_invalid_values(s, eq='beta') == [True, False, False, True, False]).all()

    s = pd.Series([1, 7.5, -99999999, np.nan])
    assert (tag_invalid_values(s, notna=True) == [False, False, False, True]).all()
    assert (tag_invalid_values(s, unique=True) == [False, False, False, False]).all()
    assert (tag_invalid_values(s, cats=[1, 7.5]) == [False, False, True, False]).all()
    assert (tag_invalid_values(s, eq=1) == [False, True, True, False]).all()
    assert (tag_invalid_values(s, ge=0) == [False, False, True, False]).all()
    assert (tag_invalid_values(s, le=0) == [True, True, False, False]).all()
    assert (tag_invalid_values(s, gt=1, lt=10) == [True, False, True, False]).all()
    assert (tag_invalid_values(s, ge=1, lt=10) == [False, False, True, False]).all()
    assert (tag_invalid_values(s, gt=10, lt=0) == [True, True, True, False]).all()

    s = pd.Series([np.nan, 15, '15', '-15', '.15', '1.5', '-.15', '-1.5', '1a', 'ab', ''])
    assert (tag_invalid_values(s, number=True) == 8 * [False] + 3 * [True]).all()
```

```{code-cell} ipython3
:tags: []

test_tag_invalid_values()
```

+++ {"tags": ["nbd-docs"]}

`group_exampler()` shows an example of dataframe observations with a randomly picked group id, where one or all observations satisfy a given condition.
Convenient to use with panel data to view full history of a single entity.

```{code-cell} ipython3
:tags: [nbd-module]

def group_exampler(group_col, sort_col=None):
    def example(df, query, all=False):
        if all:
            size = df.groupby(group_col).size().to_frame('group')
            size['query'] = df.query(query).groupby(group_col).size()
            example_pool = size.query('group == query').index.values
        else:
            example_pool = df.query(query)[group_col].values
        if len(example_pool) == 0:
            return f'No groups found for query="{query}", all={all}'
        example_group = np.random.choice(example_pool)
        example_df = df[df[group_col] == example_group]
        if sort_col is not None:
            example_df = example_df.sort_values(sort_col)
        return example_df
    return example
```

+++ {"tags": ["nbd-docs"]}

Example with a randomly generated panel dataframe.

```{code-cell} ipython3
:tags: [nbd-docs]

df = pd.DataFrame([[i, t] for i in range(5) for t in range(3)], columns=['i', 't'])
df['x'] = np.random.randint(-10, 11, len(df))
pd.DataFrame.example = group_exampler(group_col='i', sort_col='t')
print('Dataframe head:')
display(df.head())
print('Example where any x > 0:')
display(df.example('x > 0'))
print('Example where all x > 0:')
display(df.example('x > 0', all=True))
```

# Tests

```{code-cell} ipython3
:tags: [nbd-module]

def test_all():
    test_download_file()
    test_tag_invalid_values()
```

```{code-cell} ipython3
:tags: []

test_all()
```

+++ {"tags": []}

# Build this module

```{code-cell} ipython3
:tags: []

from reseng.nbd import Nbd
nbd = Nbd('reseng')
nbd.nb2mod('util.ipynb')
```
