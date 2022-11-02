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
title: "Resource usage"
format:
  html: 
    code-fold: true
    ipynb-filters:
      - reseng/nbd.py filter-docs
---
```

+++ {"tags": ["nbd-docs"]}

Resource usage monitoring can be done from outside of process - which measures process as a whole, or from inside.
Outside is easier, but less precise.

This module provides a resource monitor class that watches a given process from a subprocess.
It uses cross-platform `psutil` package to read process information.
I/O stats are not available on MacOS.

+++ {"tags": []}

[Memory usage](https://medium.com/survata-engineering-blog/monitoring-memory-usage-of-a-running-python-program-49f027e3d1ba) - medium article.

To test disk I/O speed on Linux:
- write: `sync; dd if=/dev/zero of=tempfile bs=1M count=1024; sync`
- read: `dd if=tempfile of=/dev/null bs=1M count=1024`

```{code-cell} ipython3
:tags: [nbd-module]

import sys
import os
import io
import time
import json
import subprocess
import inspect
import warnings
import functools

import psutil
from psutil._common import bytes2human
```

+++ {"tags": ["nbd-docs"]}

# Resource usage monitor

`ResourceMonitor` object starts an external process that logs resource usage.
After monitor is stopped, usage log can be reviewed, saved and visualized.

```{code-cell} ipython3
:tags: [nbd-module]

def usage_log(pid, interval=1):
    """Regularly write resource usage to stdout."""
    # local imports make function self-sufficient
    import time, psutil

    p = psutil.Process(pid)

    def get_io():
        if psutil.MACOS:
            # io_counters() not available on MacOS
            return (0, 0, 0, 0)
        elif psutil.WINDOWS:
            x = p.io_counters()
            return (x.read_bytes, 0, x.write_bytes, 0)
        else:
            x = p.io_counters()
            return (x.read_bytes, x.read_chars, x.write_bytes, x.write_chars)

    print('time,cpu,memory,read_bytes,read_chars,write_bytes,write_chars')
    p.cpu_percent()
    io_before = get_io()
    while True:
        io_after = get_io()
        io_rate = tuple((x1 - x0) / interval for x0, x1 in zip(io_before, io_after))
        io_before = io_after
        line = (time.time(), p.cpu_percent(), p.memory_info().rss) + io_rate
        print(','.join(str(x) for x in line), flush=True)
        time.sleep(interval)        
    
class ResourceMonitor:
    def __init__(self, pid=None, interval=1):
        self.pid = os.getpid() if pid is None else pid
        self.interval = interval
        self.tags = []
        self.df = None
        if psutil.MACOS:
            warnings.warn('Disk I/O stats are not available on MacOS.')

    def start(self):
        code = inspect.getsource(usage_log) + f'\nusage_log({self.pid}, {self.interval})'
        self.process = subprocess.Popen([sys.executable, '-c', code], text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def stop(self):
        self.process.terminate()
        import pandas as pd
        log_data = self.process.stdout.read()
        if log_data.count('\n') < 2:
            warnings.warn('ResourceMonitor: no entries in monitor log, execution time may be too short.')
            return            
        df = pd.read_csv(io.StringIO(log_data))
        df['elapsed'] = df['time'] - df.loc[0, 'time']
        self.df = df.set_index('elapsed')

    def tag(self, label):
        self.tags.append((time.time(), label))

    def plot(self):
        if self.df is None:
            print('ResourceMonitor: no entries in monitor log, execution time may be too short.')
            return
        
        import matplotlib.pyplot as plt
        
        # newer versions of mpl show a warning on ax.set_yticklabels()
        # other ways to fix the problem:
        # https://stackoverflow.com/questions/63723514/userwarning-fixedformatter-should-only-be-used-together-with-fixedlocator
        warnings.filterwarnings('ignore', message='FixedFormatter should only be used together with FixedLocator')
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        ax = axes[0][0]
        ax.plot(self.df['cpu'])
        ax.set_title('cpu')

        ax = axes[1][0]
        ax.plot(self.df['memory'])
        ax.set_title('memory')
        ax.set_yticklabels([bytes2human(x) for x in ax.get_yticks()])

        ax = axes[0][1]
        ax.plot(self.df['read_bytes'], label='bytes')
        ax.plot(self.df['read_chars'], label='chars')
        ax.set_title('read')
        ax.legend()
        ax.set_yticklabels([bytes2human(x) for x in ax.get_yticks()])

        ax = axes[1][1]
        ax.plot(self.df['write_bytes'], label='bytes')
        ax.plot(self.df['write_chars'], label='chars')
        ax.set_title('write')
        ax.legend()
        ax.set_yticklabels([bytes2human(x) for x in ax.get_yticks()])

        t0 = self.df.loc[0, 'time']
        for ax in axes.flatten():
            y = min(l.get_data()[1].min() for l in ax.lines)
            for tag in self.tags:
                ax.text(tag[0] - t0, y, tag[1], rotation='vertical')

    def dump(self, filepath):
        d = {'tags': self.tags,
             'data': self.df.to_csv()}
        json.dump(d, open(filepath, 'w'))

    @classmethod
    def load(cls, filepath):
        import pandas as pd
        d = json.load(open(filepath))
        m = cls()
        m.tags = d['tags']
        m.df = pd.read_csv(io.StringIO(d['data'])).set_index('elapsed')
        return m

    
def _use_cpu(t):
    t0 = time.time()
    while time.time() - t0 < t:
        x = 1

def _use_mem(s, n):
    x = []
    for _ in range(n):
        x += [1] * s * 1_000_000
        time.sleep(1)

def _write(f, size_mb):
    size = size_mb * 2**20
    count = 0
    block_size = 8 * 2**10
    data = b'a' * block_size
    f.seek(0)
    while count < size:
        count += f.write(data)
        f.flush()

def _read(f):
    block_size = 8 * 2**10
    f.seek(0)
    while f.peek():
            f.read(block_size)

            
def test_resource_monitor():
    from tempfile import TemporaryFile, NamedTemporaryFile

    mon = ResourceMonitor(interval=0.1)
    mon.start()
    time.sleep(2)
    mon.tag('cpu v')
    _use_cpu(2)
    mon.tag('cpu ^')
    time.sleep(1)
    mon.tag('mem1 v')
    _use_mem(30, 2)
    mon.tag('mem1 ^')
    time.sleep(1)
    mon.tag('mem2 v')
    _use_mem(10, 2)
    mon.tag('mem2 ^')
    time.sleep(1)
    with TemporaryFile() as tf:
        mon.tag('write v')
        _write(tf, 1000)
        mon.tag('write ^')
        time.sleep(1)
        mon.tag('read v')
        _read(tf)
        mon.tag('read ^')
    time.sleep(1)
    mon.stop()
    mon.plot()

def test_resource_monitor_serialization():
    from tempfile import TemporaryFile, NamedTemporaryFile
    
    m1 = ResourceMonitor(interval=0.2)
    m1.start()
    time.sleep(1)
    m1.tag('start')
    _use_cpu(2)
    m1.tag('stop')
    time.sleep(1)
    m1.stop()

    with NamedTemporaryFile() as tf:
        m1.dump(tf.name)
        m2 = ResourceMonitor.load(tf.name)
        m2.plot()
```

Example: use CPU, then use memory.

```{code-cell} ipython3
:tags: [nbd-docs]

mon = ResourceMonitor(interval=0.1)
mon.start()
time.sleep(1)
mon.tag('cpu v')
_use_cpu(1)
mon.tag('cpu ^')
time.sleep(1)
mon.tag('mem1 v')
_use_mem(30, 1)
mon.tag('mem1 ^')
time.sleep(1)
mon.stop()
mon.plot()
```

```{code-cell} ipython3
:tags: []

test_resource_monitor()
```

```{code-cell} ipython3
:tags: []

test_resource_monitor_serialization()
```

+++ {"tags": ["nbd-docs"]}

# Decorator for function runtime

Decorator `log_start_finish()` will print function start and total runtime at function finish, showing function name and argument values.

```{code-cell} ipython3
:tags: [nbd-module]

def func_sig(f, *args, **kwargs):
    """Return string representing function with argument values."""
    import pandas as pd
    def arg2str(x):
        if isinstance(x, pd.Series):
            return f'series({len(x)})'
        if isinstance(x, pd.DataFrame):
            return f'dataframe{x.shape}'
        s = str(x)
        if len(s) <= 10:
            return s
        else:
            return s[:9] + '…'
    a = []
    for v in args:
        a.append(arg2str(v))
    for k, v in kwargs.items():
        a.append(f'{k}={arg2str(v)}')
    a = ', '.join(a)
    return f'{f.__name__}({a})'

def log_start_finish(f):
    """Print function call signature on start and on finish with total runtime."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        sig = func_sig(f, *args, **kwargs)
        t0 = time.time()
        print(f'{time.asctime()}: {sig} started.')
        res = f(*args, **kwargs)
        dt = time.time() - t0
        print(f'{time.asctime()}: {sig} finished in {dt:.2f} seconds.')
        return res
    return wrapper
```

+++ {"tags": ["nbd-docs"]}

Example.

```{code-cell} ipython3
:tags: [nbd-module, nbd-docs]

#| code-fold: false
def test_log_start_finish():
    import pandas as pd

    @log_start_finish
    def func(x, d):
        time.sleep(0.5)
        return x + 1

    func(1, d=pd.DataFrame(index=range(1000), columns=range(5)))
```

```{code-cell} ipython3
:tags: [nbd-docs]

#| code-fold: false
test_log_start_finish()
```

Also works under multiprocessing, although output can get scrambled if multiple processes try to print at the same time. A more robust solution for multiprocessing can use [logging](https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes) module.

```{code-cell} ipython3
import multiprocessing

@log_start_finish
def func(x):
    time.sleep(0.5 + x/10)
    return x + 1

with multiprocessing.Pool(2) as pool:
    result = pool.map(func, range(4))
result
```

# Tests

```{code-cell} ipython3
:tags: [nbd-module]

def test_all():
    test_resource_monitor()
    test_resource_monitor_serialization()
    test_log_start_finish()
```

```{code-cell} ipython3
:tags: []

test_all()
```

+++ {"tags": []}

# Build this module

```{code-cell} ipython3
:tags: []

from reseng.nbd import Nbd
nbd = Nbd('reseng')
nbd.nb2mod('monitor.ipynb')
```
