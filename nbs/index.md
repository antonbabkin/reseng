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
title: "Research Engineering"
format:
  html: 
    code-fold: true
#    ipynb-filters:
#      - reseng/nbd.py filter-docs
---
```

This is a top level notebook that includes all high level tasks of the project.

+++

# Initialization

Run code in this section when you start working with the project.
It will create symbolic links necessary for file discovery within project directory structure.
If project is used as a library, importing code must call the `init()` function.

Import of project's Python package `reseng` from notebooks requires the package folder to be on import path.
The cell below achieves that by creating a symbolic link to package folder from the notebooks folder.

It is possible to commit symlinks to Git, but a subtle issue exists on Windows.
Even though symlinks can be enabled in Windows and Git settings, they do not work for submodules.
When parent repo is cloned and symlinks are initialized, the ones that point to yet-to-be-cloned submodule become invalid because submodule directories do not exist yet.
To keep things uniform, manual symlink creation by the code below is required for all operating systems.
Add symlinks to `.gitignore` to avoid confusion.

Project root detection can be done by simply checking the `__file__` variable.
Unlike `nbd`, here we are looking for this project's root, and not for caller project's root.

```{code-cell} ipython3
:tags: [nbd-module]

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
```

Run initialization in the notebook.

```{code-cell} ipython3
:tags: []

init()
```

# Build this module

```{code-cell} ipython3
:tags: []

from reseng.nbd import Nbd
nbd = Nbd('reseng')
nbd.nb2mod('index.ipynb')
```
