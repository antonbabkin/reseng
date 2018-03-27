'''Module for "chap4.ipynb" notebook.'''
print('Hello, chap4!')

from . import chap2, chap3
from .chap3.sec2 import safe, dangerous

s = chap2.df.sum()
factor = float(chap3.sec1.x)