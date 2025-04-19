<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Getting started with antsibull-nox

`antsibull-nox` is a tool for testing [Ansible collections](https://docs.ansible.com/ansible/devel/collections_guide/).
Before you get started, ensure that you:

- [Create an Ansible collection](https://docs.ansible.com/ansible/devel/dev_guide/developing_modules_in_groups.html) or have a collection project available.
- Become familiar with the basics of [developing collections](https://docs.ansible.com/ansible/devel/dev_guide/developing_collections.html).

## Adding basic tests to your collection

`antsibull-nox` defines collection tests in a `noxfile.py` file.

1. Run `antsibull-nox init` in the root of your collection.
   The root is the directory that contains `galaxy.yml`.

    That creates the `noxfile.py` and `antsibull-nox.toml` files shown below.

1. Ensure your `galaxy.yml` file contains values for the `name` and `namespace` fields at a minimum.

The **`noxfile.py`** file:
```python
# The following metadata allows Python runners and nox to install the required
# dependencies for running this Python script:
#
# /// script
# dependencies = ["nox>=2025.02.09", "antsibull-nox"]
# ///

import sys

import nox


# We try to import antsibull-nox, and if that doesn't work, provide a more useful
# error message to the user.
try:
    import antsibull_nox
except ImportError:
    print("You need to install antsibull-nox in the same Python environment as nox.")
    sys.exit(1)


antsibull_nox.load_antsibull_nox_toml()


# Allow to run the noxfile with `python noxfile.py`, `pipx run noxfile.py`, or similar.
# Requires nox >= 2025.02.09
if __name__ == "__main__":
    nox.main()
```

The **`antsibull-nox.toml`** file:
```toml
[sessions]

[sessions.lint]
# disable reformatting for now
run_isort = false

# disable reformatting for now
run_black = false

# Add more configuration settings here to adjust to your collection;
# see https://ansible.readthedocs.io/projects/antsibull-nox/config-file/#basic-linting-sessions

[sessions.docs_check]
# Add configuration settings here to adjust to your collection;
# see https://ansible.readthedocs.io/projects/antsibull-nox/config-file/#collection-documentation-check
```

## Running all tests against your collection

After you add the `noxfile.py` and `antsibull-nox.toml` files to your collection root, you can run the tests as follows:

1. Install `antsibull-nox`, which also installs `nox`.

    ```console
    pip install antsibull-nox
    ```

1. Run `nox` in the collection root to run all tests.

Alternatively, you do not have to install `antsibull-nox` and can run either of the following commands in the collection root:

- `pipx run noxfile.py`
- `uv run noxfile.py`

## Running specific tests against your collection

By default, nox runs all tests that you add to the `noxfile.py` file.
However, the more sessions a `nox` test suite contains, the more useful it is to run only some of the test sessions.

1. Run `nox --list` to list all available test sessions.
1. Run `nox -e <session>` to run a specific test session:

```bash
# List all test sessions
nox --list
pipx run noxfile.py --list
uv run noxfile.py --list

# Run only the 'lint' session
nox -e lint
pipx run noxfile.py -e lint
uv run noxfile.py -e lint
```

## Reusing virtual environments

For each run, `nox` recreates the virtual environment for every session.
You can re-use virtual environments in subsequent runs by passing the `-R` parameter.

```bash
# Reuse existing virtual environments
nox -R
pipx run noxfile.py -R
uv run noxfile.py -R
```

Alternatively, use a combination with the `-e` parameter:

```bash
# Run only 'lint' session and reuse existing virtual environments
nox -Re lint
pipx run noxfile.py -Re lint
uv run noxfile.py -Re lint
```

## Formatting code before commits

If present, the `formatters` session reformats Python code and should be run before a commit is made.
This session is included with the `lint` session, which takes longer because it does additional linting.

```bash
# Reformat code
nox -Re formatters
pipx run noxfile.py -Re formatters
uv run noxfile.py -Re formatters
```

!!! note
    Whether or not a collection has a `formatters` section depends on the parameters passed to `antsibull_nox.add_lint_sessions()` in the `noxfile.py` file.
    In the example in the previous section, `run_isort=False` and `run_black=False` disable both currently supported formatters.
    In this case, `antsibull-nox` does not add the `formatters` session because it would be empty.

## Dependent collections

By default, antsibull-nox will use `ansible-galaxy collection list` to find collections,
will look in adjacent directories,
and will download and install missing collections needed to run tests in the `.nox` cache directory.

More precisely:

1. If the current checked out collection is part of a tree structure `ansible_collections/<namespace>/<name>/`,
   then antsibull-nox will inspect all collections that are part of that tree and use them.

1. If the current checked out collection is not part of such a tree structure,
   then antsibull-nox will look for adjacent directories of the form `<namespace>.<name>`.

1. If the environment variable `ANTSIBULL_NOX_IGNORE_INSTALLED_COLLECTIONS` is not set to `true`,
   antibull-nox will call `ansible-galaxy collection list` to find all installed collections.

1. If more collections are needed,
   and `ANTSIBULL_NOX_INSTALL_COLLECTIONS` is not set to `never`,
   antsibull-nox will download and install them into the `.nox` cache directory.

In the included GitHub Action, `ANTSIBULL_NOX_IGNORE_INSTALLED_COLLECTIONS` is always set to `true`.
This avoids using collections from the Ansible community package that is installed in GitHub's default images.
