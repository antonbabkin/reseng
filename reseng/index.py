#!/usr/bin/env python
# coding: utf-8

import os
import importlib
from pathlib import Path

def init():
    """Initialize project file structure by recreating symlinks to package and all submodule packages.
    Safe to run multiple times.
    """
    proj_name = 'reseng'
    submods = []
    
    submod_list = ' and submodules ' + ', '.join(f'"{x}"' for x in submods) if submods else ''
    print(f'Initializing project "{proj_name}"{submod_list}...')
    
    root_dir = _this_proj_root()
    print(f'  Project "{proj_name}" root directory: "{root_dir}"')
    
    _recreate_dir_symlink(f'nbs/{proj_name}', f'../{proj_name}', root_dir)
    importlib.import_module(proj_name) # test
    for submod_name in submods:
        _recreate_dir_symlink(f'{proj_name}/{submod_name}', f'../submodules/{submod_name}/{submod_name}', root_dir)
        importlib.import_module(f'{proj_name}.{submod_name}') # test
    
    print(f'Initialization of "{proj_name}" finished.\n')

def _this_proj_root():
    """Return abs path to this project's root dir."""
    try:
        # caller is "index.py" module
        caller_dir = Path(__file__).parent.resolve()
    except Exception as e:
        if str(e) != "name '__file__' is not defined": raise
        # caller is "index.ipynb" notebook
        caller_dir = Path.cwd()
    return caller_dir.parent

def _recreate_dir_symlink(link, targ, root):
    """Remove and create new symlink from `link` to `targ`.
    `link` must be relative to `root`.
    `targ` must be relative to directory containing `link`.
    Example: _recreate_dir_symlink('nbs/reseng', '../reseng', Path('/path/to/proj/root'))
    """
    link = (root / link).absolute()
    assert (link.parent / targ).is_dir()
    link.unlink(missing_ok=True)
    link.symlink_to(Path(targ), target_is_directory=True)
    link_res = link.resolve()
    assert link_res.is_dir()
    print(f'  symlink: "{link.relative_to(root)}" -> "{link_res.relative_to(root)}"')

