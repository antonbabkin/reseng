#!/usr/bin/env python
# coding: utf-8

import pathlib
import pickle
import functools
from typing import Union


def simplecache(path: Union[str, pathlib.Path]):
    """Pickle function's returned value. Function returns pickled value if it exists.
    If `path` is str, may use "{}" placeholders to be filled from function arguments.
    Placeholders must be consistent with function call arguments ({} for args, {...} for kwargs).
    """
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            p = path
            if isinstance(p, str):
                p = pathlib.Path(p.format(*args, **kwargs))
            if p.exists():
                print(f'Reading {func.__name__}() cached result from "{p}".')
                return pickle.load(p.open('rb'))
            else:
                res = func(*args, **kwargs)
                print(f'Writing {func.__name__}() result to cache at "{p}".')
                p.parent.mkdir(parents=True, exist_ok=True)
                pickle.dump(res, p.open('wb'), protocol=5)
                return res
        return wrapped
    return wrapper

def test_simplecache():
    import tempfile
    import uuid
    import shutil

    try:
        p = pathlib.Path(tempfile.gettempdir())/uuid.uuid4().hex
        @simplecache(p)
        def test():
            print('--> calculating')
            return 1

        print('calculate')
        assert test() == 1
        print('load cache')
        assert test() == 1
        p.unlink()
        print('calculate')
        assert test() == 1

        p0 = pathlib.Path(tempfile.gettempdir())/uuid.uuid4().hex
        p0.mkdir()
        p1 = p0/'1'
        p2 = p0/'2'
        @simplecache(str(p0)+'/{x}')
        def test(x):
            print('--> calc', x)
            return x

        print('calculate')
        assert test(x=1) == 1
        print('calculate')
        assert test(x=2) == 2
        print('load cache')
        assert test(x=1) == 1

    finally:
        p.unlink()
        shutil.rmtree(p0)


def test_all():
    test_simplecache()

