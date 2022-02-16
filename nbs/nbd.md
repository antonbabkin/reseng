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

+++ {"tags": []}

# NBD
**Development in the notebook**

This approach was greatly inspired by the [nbdev](https://github.com/fastai/nbdev) project.

+++

**Directory structure requirements**: Package, subpackages and modules should be importable both from a notebook and from a module.  
Options:
- `cd` to project root in the notebook before doing imports. Simple `%cd ..` will work (can be `%cd ../..` for subpackage notebooks), but can not be executed repeatedly. Or a loop that goes `cd ..` until at root.
- Create symlink to package dir at the same dir where the notebook is. Needs to be repeated for each subpackage. **This approach is taken here.**
- `pip install -e .`. Requires package to be pip-installable properly.

It would be helpful to be able to identify current notebook file name, but this is not easy to do. There is a long standing open [issue](https://github.com/jupyter/notebook/issues/1000) on GH, and a default way to do this may be added in notebook v7.

+++ {"tags": []}

## nbconvert

At the core of the approach is `nbconvert`, and one could use just that.

`nbconvert` can be configured to filter out unwanted cells with `RegexRemovePreprocessor` or `TagRemovePreprocessor`.

If we want to match anywhere in the cell we need:

`patterns=['(?ms).*ABRA']`

where `(?ms)` are regex flags: re.M (multi-line), re.S (dot matches all)

Example below shows how to use `nbconvert` API to export notebook to a script and only keep cells that start with `#nbd module`.

```{code-cell} ipython3
import nbconvert
prep_select_module_cells = nbconvert.preprocessors.RegexRemovePreprocessor(patterns=['(?!#nbd module)'])
exporter = nbconvert.exporters.PythonExporter(preprocessors=[prep_select_module_cells], exclude_input_prompt=True)
script, _ = exporter.from_filename('notebook.ipynb')
```

## Cell flagging

In order to selective export cells, they need to be flagged.

One option is to use special text in cells. `# comments` are natural for code cells. For Markdown, we can use `<!--- HTML comments -->` or Markdown named links: `[nbd]: # "flag1 flag2"`. See this [SO question](https://stackoverflow.com/q/4823468) for different Markdown comment alternatives.

Another option is to use cell tags.

```{code-cell} ipython3
:tags: [nbd-module]

import os
import re
from pathlib import Path
import inspect

import nbconvert
import nbformat
```

+++ {"tags": []}

## Nbd class

`Nbd` class adds extra functionality on top of `nbconvert`.

The first thing to do is to identify project root path. This is done by going up until directory contains both `nbs` and package (`reseng` in this case) folders. The main challenge is to choose starting path from where to go up.

We can't use `__file__`, because it will always point to location of the `nbd.py` file, even if it is imported from somewhere outside of current project. This will limit use of `nbd` as a library.

Instead, I inspect call stack to identify what called the `Nbd` class initialization. If the caller is an interactive interpreter, identfied by common interpreter names, then search up from current working directory. Otherwise the caller must be some other file, in which case, file parent is used as a starting point.

```{code-cell} ipython3
:tags: [nbd-module]

class Nbd:
    nbs_dir_name = 'nbs'
    
    def __init__(self, pkg_name):
        self.pkg_name = pkg_name
        self.root = self._locate_root_path()
        self.pkg_path = self.root / pkg_name
        self.nbs_path = self.root / self.nbs_dir_name
        self._make_symlinks()
        
    def _locate_root_path(self):
        # call stack: 0=this function, 1=__init__(), 2=caller
        caller = inspect.stack()[2].filename
        interpreters = ['<ipython-input', 'xpython_', 'ipykernel_', '<stdin>']
        if any(x in caller for x in interpreters):
            # class initialized from interactive shell or notebook
            p0 = '.'
        else:
            # class initialized from module
            p0 = caller
        p = p0 = Path(p0).resolve()
        while p != p.anchor:
            pkg_dir = p / self.pkg_name
            nbs_dir = p / self.nbs_dir_name
            if pkg_dir.exists() and nbs_dir.exists():
                return p
            p = p.parent
        raise Exception(f'Could not find project root above "{p0}".')
        
    def _make_symlinks(self):
        # support for nested subpackages can be added by recursing into subdirs of nbs/ and making links in them
        cur_dir = Path.cwd()
        os.chdir(self.nbs_path)
        link = Path(self.pkg_name)
        if link.exists():
            assert link.is_symlink(), f'Symbolic link expected at "{link.absolute()}".'
        else:
            to = Path(f'../{self.pkg_name}')
            link.symlink_to(to, target_is_directory=True)
            link = link.absolute().relative_to(self.root)
            to = to.resolve().relative_to(self.root)
            print(f'Creating symbolic link "{link}" -> "{to}"')
            
        os.chdir(cur_dir)
```

```{code-cell} ipython3
:tags: []

def test_nbd_init():
    Path('reseng').unlink(missing_ok=True)
    nbd = Nbd('reseng')
    print('Project root:', nbd.root)
    pkg_dir = Path('reseng')
    print('Package files:', ', '.join(str(p.relative_to(pkg_dir)) for p in pkg_dir.iterdir()))
test_nbd_init()
```

## Conversion to module

`Nbd.nb2mod()` exports cells tagged with `nbd-module` to a script, mirroring relative path to the notebook in the package folder.

Helper function `Nbd._relative_import()` replaces absolute import from the project package with relative ones. Relative import statements are good for package portability, but can not be used in a notebook.

**Alternative.** Jupytext can automatically maintain script version of the notebook. For example, this notebook can be configured to exist in three formats: .ipynb and .md in `nbs` folder and .py in `reseng` folder by setting in the notebook metadata: `"formats": "nbs///ipynb,nbs///md:myst,reseng///py:nomarker"`. We can use `ipynb-active` cell tags to comment out unwanted code in the script.  
One limitation of this automatic conversion is that absolute paths are not changed to relative. So modules will not corretly import other package modules, unless execution is started from a folder where package or it's symlink is. But then the package can not be used as a dependency in another project.

```{code-cell} ipython3
:tags: [nbd-module]

def __relative_import(self, line, script_rel_path):
    """Replace absolute import statement in a line with relative.
    `script_rel_path` must be relative to package dir.
    """
    pattern = r'^(\s*)from \s*(\S+)\s* import (.*)$'
    m = re.match(pattern, line)
    if not m: 
        return line
    indent, abs_module, obj = m.groups()
    if not abs_module.startswith(self.pkg_name):
        return line
    
    module_as_rel_path = Path(*abs_module.split('.')[1:])
    script_rel_path = Path(script_rel_path)
    common_prefix = Path(os.path.commonpath([module_as_rel_path, script_rel_path]))
    module_rel_to_prefix = module_as_rel_path.relative_to(common_prefix).parts
    script_rel_to_prefix = script_rel_path.relative_to(common_prefix).parts
    rel_module = '.' * len(script_rel_to_prefix) + '.'.join(module_rel_to_prefix)
    
    return f'{indent}from {rel_module} import {obj}'
Nbd._relative_import = __relative_import
```

```{code-cell} ipython3
:tags: []

def test_relative_import():
    from types import SimpleNamespace
    x = SimpleNamespace(pkg_name='pkg')
    tests = [
        ('a.py', 'not an import statement', 'not an import statement'),
        ('a.py', 'from not_pkg import obj', 'from not_pkg import obj'),
        ('a2.py', 'from pkg import a1', 'from . import a1'),
        ('a2.py', '    from pkg import a1', '    from . import a1'),
        ('a2.py', 'from pkg.a1 import b', 'from .a1 import b'),
        ('a/b2.py', 'from pkg.a import b1', 'from . import b1'),
        ('a2/b.py', 'from pkg import a1', 'from .. import a1'),
        ('a2/b.py', 'from pkg.a1 import b', 'from ..a1 import b'),
        ('a/b/c2.py', 'from pkg.a.b import c2', 'from . import c2'),
        ('a/b2/c.py', 'from pkg.a import b1', 'from .. import b1'),
        ('a/b2/c.py', 'from pkg.a.b1 import c', 'from ..b1 import c'),
        ('a2/b/c.py', 'from pkg.a1.b import c', 'from ...a1.b import c')
    ]
    for file, line, expected in tests:
        assert __relative_import(x, line, file) == expected
test_relative_import()
```

```{code-cell} ipython3
:tags: [nbd-module]

def __nb2mod(self, nb_rel_path):
    """Convert notebook to script, only including cells tagged with "nbd-module".
    `nb_rel_path` is relative to project's notebook directory."""
    nb_rel_path = Path(nb_rel_path)
    nb_path = self.nbs_path / nb_rel_path
    assert nb_path.is_file(), f'Notebook not found at "{nb_path}".'
    nb = nbformat.read(nb_path, nbformat.current_nbformat)
    nb.cells = [c for c in nb.cells 
                if ((c.cell_type == 'code') 
                    and ('tags' in  c.metadata)
                    and ('nbd-module' in c.metadata.tags))]
    exporter = nbconvert.exporters.PythonExporter(exclude_input_prompt=True)
    script, _ = exporter.from_notebook_node(nb)
    mod_path = self.pkg_path / nb_rel_path.with_suffix('.py')

    # convert abs to rel imports
    script = '\n'.join(self._relative_import(l, mod_path.relative_to(self.pkg_path))
                       for l in script.split('\n'))

    mod_path.parent.mkdir(parents=True, exist_ok=True)
    mod_path.write_text(script)

    src = nb_path.relative_to(self.root)
    dst = mod_path.relative_to(self.root)
    print(f'Converted notebook "{src}" to module "{dst}".')
Nbd.nb2mod = __nb2mod
```

+++ {"tags": []}

# Build this module

```{code-cell} ipython3
:tags: []

nbd = Nbd('reseng')
nbd.nb2mod('nbd.ipynb')
```

To test, restart kernel, build again, but now using the module itself.

```{code-cell} ipython3
:tags: []

from reseng.nbd import Nbd
nbd = Nbd('reseng')
nbd.nb2mod('nbd.ipynb')
```
