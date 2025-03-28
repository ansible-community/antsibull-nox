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

The basic linting session, `lint`, comes with three sessions it depends on:

* `formatters`: runs `isort` and `black` to sort imports and format the code.
  During a regular run, the formatting is directly applied.
  In CI, the sorting order and formatting is checked, and the tests fail if it is not as expected.

* `codeqa`: runs `flake8` and `pylint`.

* `typing`: runs `mypy`.

!!! note
    CI is currently detected by checking for the `GITHUB_ACTIONS` environment variable.
    This might change in the future to support other CI systems.
    If your CI system is not supported, you can simply set `GITHUB_ACTIONS` to an arbitrary value before running `nox` in CI.

These sessions can be added with `antsibull_nox.add_lint_sessions()`.

Which of the linters should be run can be configured
(the extra sessions are not added if they are empty),
and there are plenty of configuration settings for the indiviual formatters/linters.

### Global settings:

* `make_lint_default: bool` (default `True`):
  Whether the `lint` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `extra_code_files: list[str] | None` (default `None`):
  An extra list of files to run the formatters and linters on.
  By default the formatters and linters run on code files in `plugins/`, `tests/unit/`, and on `noxfile.py`.
  If you have other scripts in your collection that should be checked, you can add them with this option.

### `isort` (part of the `formatters` session):

* `run_isort: bool` (default `True`):
  Whether to run `isort`.

* `isort_config: str | os.PathLike | None` (default `None`):
  Allows to specify a config file.
  Use a relative path to `noxfile.py`.
  Note that right now antsibull-nox will not supply any default config file,
  but this might change in the future.

* `isort_package: str` (default `"isort"`):
  The package to install for `isort` in this session.
  You can specify a value here to add restrictions to the `isort` version,
  or to pin the version,
  or to install the package from a local repository.

### `black` (part of the `formatters` session):

* `run_black: bool` (default `True`):
  Whether to run `black`.

* `run_black_modules: bool | None` (default `True`):
  Whether to run `black` also for module utils, modules, and related unit tests.
  If your collection supports Python 2.7 for modules,
  and for example needs to use the `u` prefix for Unicode strings,
  you can use this to avoid reformatting of that code (which for example removes the `u` prefix).

* `black_config: str | os.PathLike | None` (default `None`):
  Allows to specify a config file.
  Use a relative path to `noxfile.py`.
  Note that right now antsibull-nox will not supply any default config file,
  but this might change in the future.

* `black_package: str` (default `"black"`):
  The package to install for `black` in this session.
  You can specify a value here to add restrictions to the `black` version,
  or to pin the version,
  or to install the package from a local repository.

### `flake8` (part of the `codeqa` session):

* `run_flake8: bool` (default `True`):
  Whether to run `flake8`.

* `flake8_config: str | os.PathLike | None` (default `None`):
  Allows to specify a config file.
  Use a relative path to `noxfile.py`.
  Note that right now antsibull-nox will not supply any default config file,
  but this might change in the future.

* `flake8_package: str` (default `"flake8"`):
  The package to install for `flake8` in this session.
  You can specify a value here to add restrictions to the `flake8` version,
  or to pin the version,
  or to install the package from a local repository.

### `pylint` (part of the `codeqa` session):

* `run_pylint: bool` (default `True`):
  Whether to run `pylint`.

* `pylint_rcfile: str | os.PathLike | None` (default `None`):
  Allows to specify a config file.
  Use a relative path to `noxfile.py`.
  Note that right now antsibull-nox will not supply any default config file,
  but this might change in the future.

* `pylint_modules_rcfile: str | os.PathLike | None` (default `None`):
  Allows to specify a config file for modules, module utils, and the associated unit tests.
  If not specified but `pylint_rcfile` is specified, `pylint_rcfile` will be used for these files.
  Use a relative path to `noxfile.py`.
  Note that right now antsibull-nox will not supply any default config file,
  but this might change in the future.

* `pylint_ansible_core_package: str` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `pylint_extra_deps: list[str] | None` (default `None`):
  Allows to specify further packages to install in this session.

### `mypy` (part of the `typing` session):

* `run_mypy: bool` (default `True`):
  Whether to run `mypy`.

* `mypy_config: str | os.PathLike | None` (default `None`):
  Allows to specify a config file.
  Use a relative path to `noxfile.py`.
  Note that right now antsibull-nox will not supply any default config file,
  but this might change in the future.

* `mypy_package: str` (default `"mypy"`):
  The package to install for `mypy` in this session.
  You can specify a value here to add restrictions to the `mypy` version,
  or to pin the version,
  or to install the package from a local repository.

* `mypy_ansible_core_package: str` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `mypy_extra_deps: list[str] | None` (default `None`):
  Allows to specify further packages to install in this session.
  This can be used for typing stubs like `types-PyYAML`, `types-mock`, and so on.

### Example code

This example is from `community.dns`,
which uses explicit config files for the formatters and linters,
and does not format modules and module utils since it relies on the `u` string prefix:

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

