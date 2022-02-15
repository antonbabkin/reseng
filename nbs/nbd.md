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

# NBD: development in the notebook

+++ {"tags": []}

# Directory structure

**Requirements**  
Package, subpackages and modules should be importable both from a notebook and from a module.

**Option 1**  
`cd` to project root in the notebook before doing imports. Simple `%cd ..` will work (can be `%cd ../..` for subpackage notebooks), but can not be executed repeatedly. Or a loop that goes `cd ..` until at root.

**Option 2**  
Create symlink to package dir at the same dir where the notebook is. Needs to be repeated for each subpackage.

**Option 3**  
`pip install -e .`. Requires package to be pip-installable properly.

+++

It would be helpful to be able to identify current notebook name, but this is not easy to do. There is a long standing open [issue](https://github.com/jupyter/notebook/issues/1000) on GH, and a default way to do this may be added in notebook v7.

```{code-cell} ipython3
#nbd module
import os
import re
from pathlib import Path
import inspect

import nbconvert
import nbformat

class Nbd:
    def __init__(self, pkg_name, nbs_dir='nbs'):
        self.pkg_name = pkg_name
        self.nbs_dir = nbs_dir
        self.root = self._locate_root_path()
        p = self.pkg_path = self.root/pkg_name
        assert p.exists() and p.is_dir()
        p = self.nbs_path = self.root/nbs_dir
        assert p.exists() and p.is_dir()
        self._make_symlinks()
        
    def _locate_root_path(self):
        # call stack: 0=this function, 1=__init__(), 2=caller
        caller = inspect.stack()[2].filename
        if any(x in caller for x in ['<ipython-input', '/xpython_', '/ipykernel_', '<stdin>']):
            # class initialized from interactive shell or notebook
            p0 = '.'
        else:
            # class initialized from a Python module
            p0 = caller
        p = p0 = Path(p0).resolve()
        while p != p.anchor:
            if (p/self.pkg_name).exists() and (p/self.nbs_dir).exists():
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
            to = f'../{self.pkg_name}'
            link.symlink_to(to, target_is_directory=True)
            link = link.absolute().relative_to(self.root)
            to = Path(to).resolve().relative_to(self.root)
            print(f'Symbolic link created "{link}" -> "{to}"')
        os.chdir(cur_dir)

    def nb2mod(self, nb_rel_path):
        """`nb_rel_path` is relative to project's notebook directory."""
        nb_rel_path = Path(nb_rel_path)
        nb_path = self.nbs_path/nb_rel_path
        assert nb_path.exists() and nb_path.is_file(), f'Notebook not found at "{nb_path}".'
        nb = nbformat.read(nb_path, nbformat.current_nbformat)
        nb.cells = [c for c in nb.cells if (c.cell_type == 'code') and ('module' in get_cell_flags(c))]
        exporter = nbconvert.exporters.PythonExporter(exclude_input_prompt=True)
        script, _ = exporter.from_notebook_node(nb)
        mod_path = self.pkg_path/nb_rel_path.with_suffix('.py')
        
        # remove #nbd lines, convert abs to rel imports
        script = '\n'.join(self._relative_import(l, mod_path.relative_to(self.root))
                           for l in script.split('\n')
                           if not l.startswith('#nbd'))
        
        mod_path.parent.mkdir(parents=True, exist_ok=True)
        mod_path.write_text(script)
        
        src = nb_path.relative_to(self.root)
        dst = mod_path.relative_to(self.root)
        print(f'Converted notebook "{src}" to module "{dst}".')
        
    def _relative_import(self, line, file_rel_path):
        """Replace line like "from pkg.subpkg.mod1 import obj" in file "pkg/subpkg/mod2.py"
        with "from .mod1 import obj"
        """
        pattern = r'^(\s*)from \s*(\S+)\s* import (.*)$'
        m = re.match(pattern, line)
        if not m: 
            return line
        indent, mod, obj = m.groups()
        if not mod.startswith(self.pkg_name):
            return line
        # mod is like "pkg.subpkg.mod1", mod_path is like "pkg/subpkg/mod2.py"
        # need to replace each part of common prefix with a dot
        mod_parts = mod.split('.')
        path_parts = list(Path(file_rel_path).parts)
        common_len = 0
        while ((common_len < len(mod_parts))
               and (common_len < len(path_parts))
               and (mod_parts[common_len] == path_parts[common_len])):
            common_len += 1
        dots = '.' * (len(path_parts) - common_len)
        rel_mod = dots + '.'.join(mod_parts[common_len:])
        return f'{indent}from {rel_mod} import {obj}'
```

```{code-cell} ipython3
nbd = Nbd('reseng')
assert nbd._relative_import('not an import statement', 'pkg/mod.py') == 'not an import statement'
assert nbd._relative_import('from reseng import mod1', 'reseng/mod2.py') == 'from . import mod1'
assert nbd._relative_import('from reseng.mod1 import obj', 'reseng/mod2.py') == 'from .mod1 import obj'
assert nbd._relative_import('from reseng.subpkg.mod1 import obj', 'reseng/subpkg/mod2.py') == 'from .mod1 import obj'
assert nbd._relative_import('from reseng.subpkg1.mod import obj', 'reseng/subpkg2/mod.py') == 'from ..subpkg1.mod import obj'
assert nbd._relative_import('from reseng.mod1 import obj', 'reseng/subpkg1/mod.py') == 'from ..mod1 import obj'
```

# Markup

See this [SO answer](https://stackoverflow.com/a/20885980/1447107) about Markdown comments.

```{code-cell} ipython3
#nbd module
def get_cell_flags(cell):
    first_line = cell.source.split('\n', 1)[0].strip()
    if cell.cell_type == 'code' and first_line.startswith('#nbd'):
        return first_line.split()[1:]
    if cell.cell_type == 'markdown' and first_line.startswith('[nbd]:'):
        return first_line.split('"')[1].split()
    return []
```

# nbconvert

+++

If we want to match anywhere in the cell we need:

`patterns=['(?ms).*ABRA']`

where `(?ms)` are regex flags: re.M (multi-line), re.S (dot matches all)

```{code-cell} ipython3
# preprocessors
prep_select_module_cells = nbconvert.preprocessors.RegexRemovePreprocessor(patterns=['(?!#nbd module)'])
exporter = nbconvert.exporters.PythonExporter(preprocessors=[prep_select_module_cells], exclude_input_prompt=True)
script, _ = exporter.from_filename('nbd_test.ipynb')
```

# Build this module

```{code-cell} ipython3
nbd = Nbd('reseng')
nbd.nb2mod('nbd.ipynb')
```