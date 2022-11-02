#!/usr/bin/env python
# coding: utf-8

from pathlib import Path
from urllib.parse import urlparse, unquote

import requests
import numpy as np
import pandas as pd


def download_file(url, dir=None, fname=None, overwrite=False):
    """Download file from given `url` and put it into `dir`.
    Current working directory is used as default. Missing directories are created.
    File name from `url` is used as default.
    Return absolute pathlib.Path of the downloaded file.
    """
    
    if dir is None:
        dir = '.'
    dpath = Path(dir).resolve()
    dpath.mkdir(parents=True, exist_ok=True)

    if fname is None:
        fname = Path(urlparse(url).path).name
    fpath = dpath / fname
    
    if not overwrite and fpath.exists():
        print(f'File {fname} already exists.')
        return fpath

    with requests.get(url) as r:
        r.raise_for_status()
        with open(fpath, 'wb') as f:
            f.write(r.content)
    
    print(f'Downloaded file {fname}.')
    return fpath 

def test_download_file():
    from .nbd import Nbd
    nbd = Nbd('reseng')

    cloned_file = nbd.root / 'LICENSE'
    downloaded_file = download_file('https://raw.githubusercontent.com/antonbabkin/reseng/master/LICENSE', nbd.root, 'LICENSE_COPY')
    assert cloned_file.open().read() == downloaded_file.open().read()
    downloaded_file.unlink()


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


def test_all():
    test_download_file()
    test_tag_invalid_values()

