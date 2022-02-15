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

# Control panel

A single place to control various high level tasks in the project.

+++

## Symbolic links

Import of project's Python package `reseng` from notebooks requires the package folder to be on import path. The cell below achieves that by creating a symbolic link to package folder from the notebooks folder. It could be much easier to commit symlinks to the repository, but such links do not easily work on Windows.

```{code-cell} ipython3
import os
from pathlib import Path
lib_dir = Path('../reseng')
assert lib_dir.exists() and lib_dir.is_dir()
lib_link = Path('reseng')
lib_link.unlink(missing_ok=True)
os.symlink(lib_dir, lib_link, target_is_directory=True)

# empty list = no submodules
for submod in []:
    submod_dir = Path(f'../submodules/{submod}/{submod}')
    assert submod_dir.exists() and submod_dir.is_dir()
    submod_link = lib_dir/submod
    submod_link.unlink(missing_ok=True)
    os.symlink(submod_dir, submod_link, target_is_directory=True)
    
# test imports
import reseng
```
