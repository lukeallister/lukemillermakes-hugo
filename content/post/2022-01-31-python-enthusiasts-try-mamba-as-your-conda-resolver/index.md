---
title: "Python enthusiasts: try mamba as your conda resolver"
date: 2022-01-31T22:22:06.000Z
categories: 
  - "data-science"
  - "tech"
tags: 
  - "conda"
  - "python"
---

Conda solves a bunch of python environment problems. It makes it easy to manage different environments and use different dependencies for different projects. But sometimes it hangs and then tells you that the packages you are trying to install won't work together--but not exactly WHY.

I spent much of the day trying to debug a conda environment that wouldn't resolve. I was met with many-minutes-long 'checking' steps and dubious messages saying that it wouldn't work--without making it clear why.

Solution:

```
conda install -n base conda-forge::mamba

```

install mamba from conda forge into the base environment

```
mamba env create -f glue-scripts.yml

```

This gave me a very reasonable explanation of what had gone wrong and what I needed to change: mysql-python hasn't been updated and it cannot run with the python I was requesting (3.8).

I replaced the \`mysql-python\` package with \`mysqlclient\` and all was well.

## Summary

Use mamba instead of conda to do everything except activate environments--it's faster and has better error messages.
