# Typst package installer

Simple CLI to install packages from a local directory or from git. **This is not
an official package manager**, I simply wanted a simple tool for myself and
decided to share it.

## Installation

```bash
uv tool install git+https://github.com/yalap13/typi
```

It can also be installed by cloning the repo and installing after with `pip` or `pipx`.

## Usage

```bash
typi <path-of-typst-package-root>
```

**Options :**

- `-u`, `--update` : Update an already installed package version
- `-l`, `--list` : Lists the installed packages and their versions
