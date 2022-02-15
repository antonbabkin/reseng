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

# Multiple kernels in Jupyter notebooks

This notebook shows how to use different kernels (Python, R and Stata) in Jupyter. Keep in mind that with this approach communication between kernels is not possible, and data can be only shared by writing it to disk in a format understood by all kernels.

Starting with Stata 17, Stata code can be directly executed from Python, and dataframes, matrices and results can be passed between Python kernel and Stata environment. See [official documentation](https://www.stata.com/python/pystata/index.html) and our [example notebook](stata.ipynb).

+++

## Setup

1. Install Stata.

On Windows, follow instructions to [link Stata Automation library](https://kylebarron.dev/stata_kernel/getting_started/).

2. Create new conda environment.

```bash
conda create -n multikernel
conda activate multikernel
conda config --env --set channel_priority strict
conda config --env --prepend channels conda-forge
conda install python=3.9 mamba
```

3. Install Jupyter Lab (will come with IPython kernel), [R Essentials](https://docs.anaconda.com/anaconda/user-guide/tasks/using-r-language/) (IRkernel, base R and some popular libraries) and [Stata kernel](https://kylebarron.dev/stata_kernel/). Add additional Python or R packages for your needs.

```bash
mamba install jupyterlab r-essentials stata_kernel pandas
```

4. Configure Stata kernel.

```bash
python -m stata_kernel.install
```

Aftewards you may need to change config file `~/.stata_kernel.conf` to point to the right version of Stata. For example, on Linux config is set to use `stata-mp`, but you may not have license for that version.

5. Install JupyterLab extension to add Stata syntax highlighting.

```bash
mamba install nodejs
jupyter labextension install jupyterlab-stata-highlight
```

+++

## Stata

Activate Stata kernel. See a wide range of usage examples [here](https://nbviewer.jupyter.org/github/kylebarron/stata_kernel/blob/master/examples/Example.ipynb).

```{code-cell} ipython3
sysuse auto
```

```{code-cell} ipython3
describe
```

```{code-cell} ipython3
reg price mpg rep78 i.foreign
```

```{code-cell} ipython3
outsheet using ../tmp/auto.csv, comma
```

## Python

Activate Python kernel.

```{code-cell} ipython3
import pandas as pd
```

```{code-cell} ipython3
df = pd.read_csv('../tmp/auto.csv')
df.sample(3)
```

# R

Activate R kernel.

```{code-cell} ipython3
library(ggplot2)

ggplot(mpg, aes(displ, hwy, colour = class)) + 
  geom_point()
```
