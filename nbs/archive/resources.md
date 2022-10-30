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

```{code-cell} ipython3
#default_exp resources
```

# Resource management

> Manage project resources such as data and images.

**This module is not currently used in active projects, and in hindsight does not add enough value to justify the overhead it creates.
Some ideas might still be useful in future projects, e.g. with bigger team and data spread across multiple storage types.**

+++

This module serves two main purposes.
- Consolidate paths to resources used across project modules.
- Provide methods to sync resources between local and remote storage locations.

Main parts of the interface, available in module namespace (`import resouces`):
- `paths`: paths to project root and remote data repo.
- `Resouce`: representation of a single file resouce.
- `add`, `get` and `remove` functions: interact with default resouce registry.

Resources are either synced or not. "Sync" resouce has local and remote paths and can be sent both ways. "Non-sync" resource has only single path.

Registered resources are added to a JSON registry file (`resources.json` in project root by default), which is intended to be version controlled by Git.

### Example 1. Refer to file and directory paths

To support portability, use absolute paths defined relative to `paths['root']`. It is encouraged to use `pathlib.Path` objects.

```python
temp_table_path = resources.paths.root / 'tmp/tab.csv'
temp_table = pd.read_csv(temp_table_path)
```

### Example 2. Read-only use of resource created and registered by others

Use `resouces.get()` without arguments to see all resources registered in the project. Pass a key argument to obtain a single resouce or a specific subset.

Non-sync resource example.
```python
raw_data_res = resources.get('raw/table/csv')
raw_data_df = pd.read_csv(raw_data_res.path)
```

Sync resource example.
```python
proc_data_res = resouces.get('proc/table/csv')
proc_data_df = pd.read_csv(proc_data_res.remote_path)
```

### Example 3. Pull-modify-push sync resource

Take something created by others, modify it and share the updated version.

```python
proc_data_res = resouces.get('proc/table/csv')
# get local copy
proc_data_res.pull()
# modify and save local copy
proc_data_df = pd.read_csv(proc_data_res.path)
modified = proc_data_df.sort_values()
modified.to_csv(proc_data_res.path)
# share updated version
proc_data_res.push()
```

### Example 4. Create and register new resource

```python
fig_res = resources.Resource(key='out/fig', path='output/fig.png', description='Rise and fall')
resources.add(fig_res)
plt.savefig(fig_res.path)
fig_res.push()
```

```{code-cell} ipython3
#export
import functools
from pathlib import Path
import shutil
import tempfile
import configparser
import json
import pickle
import datetime
import logging
import sys
```

```{code-cell} ipython3
#export
class Paths():
    """Collection of project paths."""
    def __init__(self, root=None):
        if root is None:
            self.root = self.locate_project_root()
        else:
            self.root = Path(root).absolute()
            
        config = configparser.ConfigParser()
        config.read(self.root / 'settings.ini')
        
        self.cache = self.abs(config['resources']['cache_dir'])
        
        self.remote = Path(config['resources']['remote_dir'])
        assert self.remote.is_absolute()
        assert self.remote.exists() and self.remote.is_dir()

    @staticmethod
    def locate_project_root():
        """Return path to project root directory.
        Root is identified by presence of "settings.ini" file.
        """
        d = Path.cwd()
        while d != d.parent:
            if (d / 'settings.ini').exists():
                return d
            d = d.parent
        raise Exception(f'Can not find project root at or above "{Path.cwd()}"')
        
    def abs(self, path):
        """Return absolutized `path`."""
        path = Path(path)
        return path if path.is_absolute() else self.root / path

paths = Paths()
```

```{code-cell} ipython3
#export
class Resource:
    """Abstraction of a single file."""
    def __init__(self, key, path, description='', sync=True, public=False):
        """Declare new resource. `key` should be a short name.
        Underlying files do not need to exist.
        `sync` enabled resources must have relative `path`, 
        they can be synced between local project directory and remote resource repository.
        """
        self.key = key
        self._raw_path = path
        self.description = description
        self.sync = sync
        self.public = public
        
        path = Path(path)
        if sync:
            assert not path.is_absolute()
            self.path = paths.abs(path)
            self.remote_path = paths.remote / path
        else:
            if not path.is_absolute():
                path = paths.abs(path)
            self.path = path
            self.remote_path = None
            
    def __repr__(self):
        return repr(self._to_dict())
    
    __str__ = __repr__

    def _to_dict(self):
        return dict(key=self.key, path=self._raw_path, description=self.description, sync=self.sync, public=self.public)
    
    @classmethod
    def _from_dict(cls, d):
        return cls(**d)
    
    def push(self):
        """Copy sync-enabled resource from local to remote."""
        if not self.sync: 
            print(f'Can not push sync-disabled resource "{self.key}"')
            return
        self.remote_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.path, self.remote_path)
        print(f'Pushed "{self.key}": {self.path} -> {self.remote_path}')
    
    def pull(self):
        """Copy sync-enabled resource from remote to local."""
        if not self.sync: 
            print(f'Can not pull sync-disabled resource "{self.key}"')
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.remote_path, self.path)
        print(f'Pulled "{self.key}": {self.remote_path} -> {self.path}')
    
    def clear(self):
        """Remove local copy of sync-enabled resource."""
        if not self.sync: 
            print(f'Can not clear sync-disabled resource "{self.key}"')
            return
        self.path.unlink()
        print(f'Removed local "{self.key}": {self.path}')
        
    def clear_remote(self):
        """Remove remote copy of sync-enabled resource."""
        if not self.sync: 
            print(f'Can not clear sync-disabled resource "{self.key}"')
            return
        self.remote_path.unlink()
        print(f'Removed remote "{self.key}": {self.path}')
    
    def publish(self):
        """Send resource to public-facing repository."""
        pass
```

```{code-cell} ipython3
#export
class Registry:
    """Registry of resources, synced with file on disk."""
    def __init__(self, registry_file='resources.json'):
        self.file = paths.abs(registry_file)

        self.resources = dict()
        if self.file.exists():
            res_dicts = json.load(self.file.open())
            for res_dict in res_dicts.values():
                res = Resource._from_dict(res_dict)
                self.resources[res.key] = res     
        else:
            self._dump()

    def _dump(self):
        """Save registry to disk.
        Records are ordered by key."""
        # Dicts iterate in the order of key insertions.
        # Assuming that json.dump() maintains that ordering.
        res_dicts = dict()
        for key in sorted(self.resources.keys()):
            res_dicts[key] = self.resources[key]._to_dict()
        json.dump(res_dicts, self.file.open('w'), indent=2)

    def add(self, res, overwrite=False):
        """Add new resource to registry."""
        if not overwrite and res.key in self.resources:
            print(f'Resource "{res.key}" already in the registry, did not overwrite.')
            return
        if res.key in self.resources:
            old_res = self.resources[res.key]
            print(f'Overwriting existing resource: {old_res}')
        self.resources[res.key] = res
        self._dump()
        print(f'Resource "{res.key}" added to registry.')
    
    def remove(self, key):
        """Remove resource with exact `key`."""
        if key not in self.resources:
            print(f'Resource "{key}" not found.')
            return
        del self.resources[key]
        self._dump()
        print(f'Resource "{key}" removed from registry.')
    
    def get(self, key_pattern='*'):
        """Return list of resources with key matching glob-like `key_pattern`.
        If match is unique, return single resource object.
        List is sorted by key.
        """
        matches = [r for k, r in self.resources.items()
                   if Path(k).match(key_pattern)]
        matches.sort(key=lambda res: res.key)
        return matches[0] if len(matches) == 1 else matches
            
```

## Module interface

```{code-cell} ipython3
#export
registry = Registry()

add = registry.add
get = registry.get
remove = registry.remove

def pull(key_pattern='*'):
    """Get resources matching `key_pattern` from remote repository."""
    for r in registry.get(key_pattern):
        if r.sync:
            r.pull()

def push(key_pattern='*'):
    """Send resources matching `key_pattern` to remote repository."""
    for r in registry.get(key_pattern):
        if r.sync:
            r.push()
```

## Tests

```{code-cell} ipython3
# TEST: Convert resource to and from dict.
d = dict(key='a/b', path='a/b.csv', description='data B', sync=True, public=True)
r = Resource._from_dict(d)
assert r._to_dict() == d
```

```{code-cell} ipython3
# TEST: Pull synced resource, update content and push back, clean up.
r = Resource('test/pull-upd-push', 'tmp/pull-upd-push.txt', 'Test pull-upd-push')
r.remote_path.parent.mkdir(parents=True, exist_ok=True)
r.remote_path.write_text('Jack')
r.pull()
assert r.path.read_text() == 'Jack'
f = r.path.open('a')
f.write(' and Jill')
f.close()
r.push()
assert r.remote_path.read_text() == 'Jack and Jill'
r.clear()
assert not r.path.exists()
r.clear_remote()
assert not r.remote_path.exists()
```

```{code-cell} ipython3
# TEST: Add, get and remove resources in registry.
r = Registry('test_resources.json')
assert r.get() == []
r.add(Resource('in/data', 'input/data.csv', 'input data'))
r.add(Resource('out/data', 'output/result.csv', 'output data'))
assert [x.key for x in r.get()] == ['in/data', 'out/data']
assert r.get('out/data').description == 'output data'
r.remove('out/data')
assert r.get().description == 'input data'
r.add(Resource('out/data', 'output/result.csv', 'output data'))
r.add(Resource('out/fig', 'output/image.png', 'output figure'))
assert [x.key for x in r.get()] == ['in/data', 'out/data', 'out/fig']
assert [x.description for x in r.get('*/data')] == ['input data', 'output data']
assert [x.description for x in r.get('out/*')] == ['output data', 'output figure']
assert r.get('out/???').description == 'output figure'
assert r.get('whole/world') == []
r.remove('in/data')
r.remove('out/data')
r.remove('out/fig')
assert r.get() == []
assert r.file.read_text() == '{}'
r.file.unlink()
```
