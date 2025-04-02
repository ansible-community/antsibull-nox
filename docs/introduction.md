<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Why antsibull-nox?

`antsibull-nox` is designed to simplify the process of testing Ansible collections through a common interface for various tools.

## Tool landscape

The CLI tool `ansible-test`, which is part of ansible-core, is the main way to [test collections](https://docs.ansible.com/ansible/devel/dev_guide/developing_collections_testing.html).
(Note that `ansible-test` is included in the `ansible-core` package, and unrelated to the PyPI package called `ansible-test`.)
Many collections also run [`ansible-lint`](https://ansible.readthedocs.io/projects/lint/) to check roles and integration tests.
[`molecule`](https://ansible.readthedocs.io/projects/molecule/) is another tool that collections run to test roles or even modules and plugins.

In addition these tools, there are many other tools that can test collections.
For example, [`antsibull-docs` includes a collection documentation linter](https://ansible.readthedocs.io/projects/antsibull-docs/collection-docs/#linting-collection-docs).
Many collections also have stricter Python linting than the `pylint` and `pep8` checks that `ansible-test` offers.
Likewise, tools such as `black` are often used with collections to format code.
Some other collections use [license checkers such as `reuse`](https://pypi.org/project/reuse/) or [spell checkers such as `codespell`](https://pypi.org/project/codespell/).

Running all these tools on collections can be non-trivial because collections do not contain Python packages directly.
Instead, at runtime, Ansible dynamically makes collections available as a Python package named `ansible_collections` that is outside the root directory of each collection.
Another factor that increases the complexity of testing collections with a combination of multiple tools is that every tool has its own set of dependencies that you need to install.

## Benefits of antsibull-nox

`antsibull-nox` is built specifically for the structure of Ansible collections unlike many other test runners, such as [tox](https://pypi.org/project/tox/), [nox](https://pypi.org/project/nox/), [pre-commit.com](https://pypi.org/project/pre-commit/).

The common interface that `antsibull-nox` provides also makes it easier for you and your contributors to run tests locally.
There is no need to install several different tools and figure out how to run them correctly.
You can simply run a single `nox` command to execute all tests after installing `antsibull-nox`.
You don't even need to bother with installation; just run either `pipx run noxfile.py` or `uv run noxfile.py`.
