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

# Logging

```{code-cell} ipython3
#default_export logging
```

```{code-cell} ipython3
:tags: []

#export
import logging
```

Log to standard output stream.

```{code-cell} ipython3
:tags: []

import sys
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s', force=True)
logging.info('hello')
```

Log to a file.

```{code-cell} ipython3
:tags: []

import tempfile
tf = tempfile.NamedTemporaryFile(delete=False)
tf.close()

logging.basicConfig(filename=tf.name, filemode='w', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s', force=True)
logging.info('hello')

print(tf.name)
with open(tf.name) as f:
    print(f.read())
```
