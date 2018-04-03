'''Module for "chap2.ipynb" notebook.'''
print('Hello, chap2!')

import pandas as pd

_n, _m = 100, 3
_data = pd.np.random.rand(_n, _m)
_answer = 2**7 - 602 // 7

df = pd.DataFrame(_data)

def summarize():
    print(df.describe())

def print_answer():
    print(_answer)
