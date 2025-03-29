<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Getting Started with antsibull-nox

antsibull-nox is a tool for testing [Ansible collections](https://docs.ansible.com/ansible/devel/collections_guide/).
We assume that you have [created an Ansible collection](https://docs.ansible.com/ansible/devel/dev_guide/developing_modules_in_groups.html)
and are familiar with basic concepts of how to [develop collections](https://docs.ansible.com/ansible/devel/dev_guide/developing_collections.html).
If not, please follow the links to appropriate parts of the Ansible docsite for more information on these topics.

## Why you (might) need antsibull-nox

The main tool for [testing collections](https://docs.ansible.com/ansible/devel/dev_guide/developing_collections_testing.html) is the CLI tool `ansible-test`,
which is included in the ansible-core package.
(Do not confuse it with the PyPI package called `ansible-test`, it is unrelated!)
Many collections also run [ansible-lint](https://ansible.readthedocs.io/projects/lint/) to check roles and integration tests,
and/or use [molecule](https://ansible.readthedocs.io/projects/molecule/) to test roles or even modules and plugins.

Besides these tools, there are many other tools that can be used to test collections.
For example, [antsibull-docs includes a collection documentation linter](https://ansible.readthedocs.io/projects/antsibull-docs/collection-docs/#linting-collection-docs),
it might be wanted to have more strict Python linting than the rather basic `pylint` and `pep8` checks of ansible-test,
or one might want to format the collection's code with formatters like `black`.

Running these tools on collections can be non-trivial since collections do not contain Python packages directly,
but during runtime in Ansible are part of `ansible_collections` Python package that is outside the collection's root directory.
Also every tool comes with its own set of dependencies and needs to be installed,
which can be quite complex if several of these tools are combined.

antsibull-nox allows to simply the testing process for collections
by providing a common interface to all these testing tools.
It differs from other test runners like [tox](https://pypi.org/project/tox/), [nox](https://pypi.org/project/nox/), [pre-commit.com](https://pypi.org/project/pre-commit/)
in that it understands Ansible collections.

This also makes it easier for contributors to your collection to run tests locally.
Instead of having to install different tools and having to figure out how run them
(for some of them you have to put your collection checkout into an `ansible_collections` tree structure),
they can simply run `nox` (assuming they installed antsibull-nox)
or `pipx run noxfile.py` or `uv run noxfile.py` (no installation necessary!).

## Adding basic tests to your collection

Add the following file as `noxfile.py` into your collection's root.
The collection's root is the directory which contains `galaxy.yml`.
The `galaxy.yml` file should contain at least `name` and `namespace`.

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


antsibull_nox.add_lint_sessions(
    run_isort=False,  # disable reformatting for now
    run_black=False,  # disable reformatting for now
    # Add more configuration settings here to adjust to your collection;
    # see https://ansible.readthedocs.io/projects/antsibull-nox/reference/#basic-linting-sessions
)
antsibull_nox.add_docs_check(
    # Add configuration settings here to adjust to your collection;
    # see https://ansible.readthedocs.io/projects/antsibull-nox/reference/#collection-documentation-check
)


# Allow to run the noxfile with `python noxfile.py`, `pipx run noxfile.py`, or similar.
# Requires nox >= 2025.02.09
if __name__ == "__main__":
    nox.main()
```

With this file present,
you can run the tests as described in the next section.

## Running tests

Then you can run these tests as follows:

1. You can install `antsibull-nox` (which also installs `nox`) with pip:
   ```console
   pip install antsibull-nox
   ```
   Afterwards you can simply run `nox` in the collection's root directory.

1. If you are using pipx, you can simply run `pipx run noxfile.py` in your collection's root directory.

1. If you are using uv, you can simply run `uv run noxfile.py` in your collection's root directory.

By default, nox runs all sessions that have been added.
You can pass `--list` on the command line to list all sessions that can be run,
and you can pass `-e <name of session>` to run a specific session:
```bash
# List all sessions
nox --list
pipx run noxfile.py --list
uv run noxfile.py --list

# Run only 'lint' session
nox -e lint
pipx run noxfile.py -e lint
uv run noxfile.py -e lint
```

!!! note
    You will notice that for every run, every session's virtual environment is recreated.
    If you prefer to re-use existing virtual environments in subsequent runs,
    you can pass the `-R` parameter:
    ```bash
    # Reuse existing virtual environments
    nox -R
    pipx run noxfile.py -R
    uv run noxfile.py -R
    ```

    It can be combined with `-e` to `-Re`
    ```bash
    # Run only 'lint' session and reuse existing virtual environments
    nox -Re lint
    pipx run noxfile.py -Re lint
    uv run noxfile.py -Re lint
    ```

!!! note
    The more sessions a nox test suite contains for a collection,
    the more useful it is to run only a few selected of these sessions.
    Which tests are the most important depends on the collection.

If present, the `formatters` session reformats the Python code
and should be run before a commit is made:
```bash
# Reformat code
nox -Re formatters
pipx run noxfile.py -Re formatters
uv run noxfile.py -Re formatters
```
It is part of the `lint` session, which does some more linting
(but takes more time).
```bash
# Reformat code and do other basic linting
nox -Re lint
pipx run noxfile.py -Re lint
uv run noxfile.py -Re lint
```

!!! note
    Whether or not a collection has a `formatters` section depends on
    the parameters passed to `antsibull_nox.add_lint_sessions()` in noxfile.py.
    In the example in the previous section,
    `run_isort=False` and `run_black=False` disable both currently supported formatters.
    antsibull-nox will then not add the `formatters` session
    (because it would do nothing useful as it would be empty).

## Basic troubleshooting

### General problems

If you get strange errors when running a session with re-used virtual environment,
it could be that your Python version changed or something else broke.
It is often a good idea to first try to re-create the virtual environment
by simply running the session without `-R` or `-r`:
```bash
# Run the lint session and re-create all virtual environments for it
nox -e lint
pipx run noxfile.py -e lint
uv run noxfile.py -e lint
```
This often resolves the problems.

### Differences between CI and local runs

If you notice that your local tests report different results than CI,
re-creating the virtual environments can also help.
Sometimes linters have newer versions with more checks that are running in CI,
while your local virtual environments are still using an older version.

### Avoid sudden CI breakages due to new versions

As a collection maintainer,
if you prefer that new tests do not suddenly appear,
you should use the `*_package` parameters to the various `antsibull.add_*()` function calls
to pin specific versions of the linters.

!!! note
    If you pin specific versions, you yourself are responsible for bumping these versions from time to time.
