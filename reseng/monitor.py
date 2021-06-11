# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/nbs/monitor.ipynb (unless otherwise specified).

__all__ = ['usage_log', 'ResourceMonitor']

# Cell
#export
import sys
import os
import io
import time
import json
import subprocess
import inspect
import warnings

import psutil
from psutil._common import bytes2human

# Cell

def usage_log(pid, interval=1):
    """Regularly write resource usage to stdout."""
    # local imports make function self-sufficient
    import time, psutil

    if psutil.MACOS:
        warnings.warn('Disk I/O stats are not available on MacOS.')

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