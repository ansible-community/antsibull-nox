<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# noxfile Reference

This document assumes some basic familiarity with Nox and `noxfile.py` files. If you want more information on these, take a look at the following resources:

* [Nox tutorial](https://nox.thea.codes/en/stable/tutorial.html);
* [Nox configuration and API](https://nox.thea.codes/en/stable/config.html).

## Basic noxfile structure

A basic `noxfile.py` using antsibull-nox looks as follows:

```python
# The following metadata allows Python runners and nox to install the required
# dependencies for running this Python script:
#
# /// script
# dependencies = ["nox>=2025.02.09", "antsibull-nox"]
# ///

import os
import sys

import nox


# We try to import antsibull-nox, and if that doesn't work, provide a more useful
# error message to the user.
try:
    import antsibull_nox
    import antsibull_nox.sessions
except ImportError:
    print("You need to install antsibull-nox in the same Python environment as nox.")
    sys.exit(1)


# Always install latest pip version.
# (This isn't strictly necessary, but something all antsibull projects do as well
# in their noxfile.py files.)
os.environ["VIRTUALENV_DOWNLOAD"] = "1"


... here you can call antsibull_nox functions to define sessions, or define your own ...


# Allow to run the noxfile with `python noxfile.py`, `pipx run noxfile.py`, or similar.
# Requires nox >= 2025.02.09
if __name__ == "__main__":
    nox.main()
```

## Basic linting sessions

TODO

```python
antsibull_nox.add_lint_sessions(
    extra_code_files=["update-docs-fragments.py"],
    isort_config="tests/nox-config-isort.cfg",
    run_black_modules=False,  # modules still support Python 2
    black_config="tests/nox-config-black.toml",
    flake8_config="tests/nox-config-flake8.ini",
    pylint_rcfile="tests/nox-config-pylint.rc",
    pylint_modules_rcfile="tests/nox-config-pylint-py2.rc",
    mypy_config="tests/nox-config-mypy.ini",
    mypy_extra_deps=[
        "dnspython",
        "types-lxml",
        "types-mock",
        "types-PyYAML",
    ],
)
```

## Collection documentation check

TODO

## REUSE and license checks

TODO

## Action groups and unwanted files checks

TODO

## Collection build and Galaxy import test

TODO

## Adding own tests that need to import from the collection structure

TODO

