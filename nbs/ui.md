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

# User interface

+++

## Initialization

Run this section to initialize your local repository after cloning. It is safe to run multiple times.

+++

### Symbolic links

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

### Git configuration

```{code-cell} ipython3
%cd ..
!nbdime config-git --enable
!git config filter.jupyternotebook.clean "jupyter nbconvert --stdin --stdout --to=notebook --ClearOutputPreprocessor.enabled=True --ClearMetadataPreprocessor.enabled=True --log-level=ERROR"
!git config filter.jupyternotebook.smudge cat
!git config filter.jupyternotebook.required true
!git config diff.jupyternotebook.command "git-nbdiffdriver diff --ignore-outputs --ignore-metadata --ignore-details"
%cd -
```
