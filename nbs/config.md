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

# Configuration and paths

```{code-cell} ipython3
#default_exp config
```

```{code-cell} ipython3
#export
import sys
import pathlib
import inspect
import configparser
```

```{code-cell} ipython3
#export
class Paths:
    """Namespace for `pathlib.Path` objects.
    Save paths at initialization or add them later with `Paths.add()`.
    """
    def __init__(self, **kwargs):
        """Use name=path kwargs to add paths in addition to defaults."""
        self.root = self.locate_root_path()
        self._path_names = ['root']
        for name, path in kwargs.items():
            self.add(name, path)
            self._path_names.append(name)
            
    def __str__(self):
        name_col_width = max(map(len, self._path_names))
        return '\n'.join(f'{n:>{name_col_width}}: {getattr(self, n)}' for n in self._path_names)

    @staticmethod
    def locate_root_path():
        """Return project root path identified by presence of ".git" directory."""
        # call stack: 0=this function, 1=__init__(), 2=caller
        caller = inspect.stack()[2].filename
        if any(x in caller for x in ['<ipython-input', '/xpython_', '/ipykernel_', '<stdin>']):
            # class initialized from interactive shell or notebook
            p0 = '.'
        else:
            # class initialized from a Python module
            p0 = caller
        p = p0 = pathlib.Path(p0).resolve()
        while p != p.parent:
            if (p/'.git').exists():
                return p
            p = p.parent
        raise Exception(f'Could not find project root above "{p0}".')
        
    def make(self, path):
        """Return resolved path. If relative path is given, resolve from project root."""
        path = pathlib.Path(path)
        if not path.is_absolute():
            path = self.root/path
        return path.resolve()
    
    def add(self, name, path):
        """Save given `path` as object attribute with given `name`."""
        setattr(self, name, self.make(path))
```

```{code-cell} ipython3
p = Paths(rel='relative/path', abs='/absolute/path')
print(p)
```

```{code-cell} ipython3
#export
class Config:
    """Read settings from INI file in project root."""
    def __init__(self):
        self.file = Paths.locate_root_path()/'settings.ini'
        self.parser = configparser.ConfigParser()
        self.parser.read(self.file)
        print(f'Module "{__name__}" read config from "{self.file}".')
        
    def get(self, key, section='DEFAULT'):
        return self.parser.get(section, key)
    def getbool(self, key, section='DEFAULT'):
        return self.parser.getboolean(section, key)
    def getint(self, key, section='DEFAULT'):
        return self.parser.getint(section, key)
    def getfloat(self, key, section='DEFAULT'):
        return self.parser.getfloat(section, key)

# module singleton, use to read config file only once on the first import
config = Config()
```

```{code-cell} ipython3
c = Config()
assert c.get('lib_name') == 'reseng'
assert not c.getbool('custom_sidebar')
assert c.getint('status') == 2
assert c.getfloat('min_python') == 3.8
```
