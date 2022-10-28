#!/usr/bin/env python
# coding: utf-8

import sys
import os
import re
from pathlib import Path
import inspect

import nbconvert
import nbformat


class Nbd:
    nbs_dir_name = 'nbs'
    
    def __init__(self, pkg_name):
        self.pkg_name = pkg_name
        self.root = self._locate_root_path()
        self.pkg_path = self.root / pkg_name
        self.nbs_path = self.root / self.nbs_dir_name
        self.tmp = self.root / 'tmp' # convenience shortcut, may not exist
        
        # verify that symlink to package dir exists inside of nbs dir
        p = self.nbs_path / pkg_name
        assert p.exists() and p.is_symlink()

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

def test_nbd_init():
    nbd = Nbd('reseng')
    print('Project root:', nbd.root)
    pkg_dir = Path('reseng')
    print('Package modules:', ', '.join(str(p.relative_to(pkg_dir)) for p in pkg_dir.iterdir() if p.suffix == '.py'))


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

def test_nbd_nb2mod():
    nbd = Nbd('reseng')
    nbd.nb2mod('nbd.ipynb')


def filter_docs():
    """Only keep cells with "nbd-docs" tag.
    Reads notebook from STDIN and prints filtered notebook to STDOUT.
    """
    nb = nbformat.reads(sys.stdin.read(), as_version=nbformat.NO_CONVERT)
    nb.cells = [
        c for c in nb.cells
        if ('tags' in c.metadata) and ('nbd-docs' in c.metadata.tags)
    ]
    nbformat.write(nb, sys.stdout)


if __name__ == '__main__':
    if sys.argv[1] == 'filter-docs':
        filter_docs()


def test_all():
    test_nbd_init()
    test_relative_import()
    test_nbd_nb2mod()

