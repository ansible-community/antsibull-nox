<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# noxfile Reference

This document assumes some basic familiarity with Nox and `noxfile.py` files. If you want more information on these, take a look at the following resources:

* [Nox tutorial](https://nox.thea.codes/en/stable/tutorial.html);
* [Nox configuration and API](https://nox.thea.codes/en/stable/config.html).

You might also want to read [Getting Started](getting-started.md) first if you haven't already done so.

## Basic noxfile structure

A basic `noxfile.py` using antsibull-nox looks as follows:

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


... here you can call antsibull_nox functions to define additional sessions ...


# Allow to run the noxfile with `python noxfile.py`, `pipx run noxfile.py`, or similar.
# Requires nox >= 2025.02.09
if __name__ == "__main__":
    nox.main()
```

## Loading the `antsibull-nox.toml` configuration

You should always add the `antsibull_nox.load_antsibull_nox_toml()` function call
as shown in the example above.
It loads the `antsibull-nox.toml` configuration file,
loads its configuration options,
and adds all sessions configured in there.

## Adding own tests that need to import from the collection structure

Some collections need additional, specific tests for collection-specific properties.
These can usually be added as regular Nox sessions
by defining a function and decorating it with `@nox.session()`.

In some cases, though, these tests need to be able to import code from the collection,
or need to be able to run `ansible-doc` or other tools on the collection
that expect the collection to be part of an `ansible_collections` tree structure.

For this, antsibull-nox provides a powerful helper function `antsibull_nox.sessions.prepare_collections()`
which prepares an `ansible_collections` tree structure in the session's temporary directory.
The tree structure can optionally also be part of `site-packages`,
to make it importable in Python code.

The function `antsibull_nox.sessions.prepare_collections()` accepts the following parameters:

* `session: nox.Session` (positional argument, **required**):
  The Nox session object.

* `install_in_site_packages: bool` (keyword argument, **required**):
  Whether to install the `ansible_collections` tree in `site-packages`.
  If set to `True`, Python code can import code from the collections.
  If set to `False`, Python code can **not** import code.

* `install_out_of_tree: bool` (keyword argument, default `False`):
  Whether to install the `ansible_collections` tree in `$TEMP`
  instead of the nox session directory.
  Setting this to `True` is not allowed if `install_in_site_packages=True`.
  This is necessary when running tools like `ansible-doc` against the tree
  that do not accept nested `ansible_collections` directory structures,
  where `ansible_collections` is found below `ansible_collections/<namespace>/<name>`
  for a collection `<namespace>.<name>`.

* `extra_deps_files: list[str | os.PathLike] | None` (default `None`):
  Paths to [collection requirements files](https://docs.ansible.com/ansible/devel/collections_guide/collections_installing.html#install-multiple-collections-with-a-requirements-file)
  whose collections should be copied into the tree structure.

* `extra_collections: list[str] | None` (default `None`):
  An explicit list of collections (form `<namespace>.<name>`)
  that should be copied into the tree structure.

The function returns `antsibull_nox.sessions.CollectionSetup | None`.
If the return value is `None`, the `ansible_collections` tree was not created for some reason.
Otherwise, an `antsibull_nox.sessions.CollectionSetup` object is returned,
which has the following properties:

* `collections_root: Path`:
  The path of the `ansible_collections` directory where all dependent collections are installed.
  Is currently identical to `current_root`, but that might change or depend on options in the future.

* `current_place: Path`:
  The directory in which the `ansible_collections` directory can be found,
  as well as in which `ansible_collections/<namespace>/<name>` points to a copy of the current collection.

* `current_root: Path`:
  The path of the ansible_collections directory that contains the current collection.
  The following is always true:
  ```python
  current_root == current_place / "ansible_collections"
  ```

* `current_collection: antsibull_nox.collection.CollectionData`:
  Data on the current collection (as in the repository).

    The object contains the following properties:

    * `collections_root_path: Path | None`:
      Identical to `current_root` above.

    * `path: Path`:
      The path where the collection repository is.

    * `namespace: str`:
      The collection's namespace, as found in `galaxy.yml`.

    * `name: str`:
      The collection's name, as found in `galaxy.yml`.

    * `full_name: str`:
      The collection's full name.
      The following is always true:
      ```python
      full_name = namespace + "." + name
      ```

    * `version: str | None`:
      The collection's version, as found in `galaxy.yml`.
      If not present in `galaxy.yml`, will be `None`.

    * `dependencies: dict[str, str]`:
      The collection's dependencies, as found in `galaxy.yml`.

    * `current: bool`:
      Always `true`.

* `current_path: Path`:
  The path of the current collection inside the collection tree below `current_root`.
  The following is always true:
  ```python
  current_path == current_root / current_collection.namespace / current_collection.name
  ```

### Example code

This example is from `community.dns`.
The `update-docs-fragments.py` script updates some docs fragments
with information from module utils to ensure that both data sources are in sync.

To be able to do this, the script needs to import the module utils.
Because of that, we set `install_in_site_packages=True`.

```python
import os

# Put this in the try/except at the top of the noxfile.py:
import antsibull_nox.sessions


# Whether the noxfile is running in CI:
# https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables#default-environment-variables
# https://docs.gitlab.com/ci/variables/predefined_variables/#predefined-variables
# https://docs.travis-ci.com/user/environment-variables/#default-environment-variables
IN_CI = os.environ.get("CI") == "true"


@nox.session(name="update-docs-fragments")
def update_docs_fragments(session: nox.Session) -> None:
    session.install(session, "ansible-core")
    prepare = antsibull_nox.sessions.prepare_collections(
        session, install_in_site_packages=True
    )
    if not prepare:
        return
    data = ["python", "update-docs-fragments.py"]
    if IN_CI:
        data.append("--lint")
    session.run(*data)
```

## Run ansible-test

antsibull-nox provides several ways to run ansible-core's testing tool `ansible-test` directly from nox.
It knows which Python versions every ansible-core release supports and picks an installed version of Python for every ansible-test session if possible,
or picks the highest supported Python version for the ansible-core release is no installed Python is found.

Most sessions can be directly added from the configuration file.
See [the configuration file reference for more details](config-file.md#run-ansible-test).
If you need to add more or very specific integration test sessions,
you can use the low-level functions mentioned below.

### Adding an explicit ansible-test session

`antsibull_nox.add_ansible_test_session()` is a low-level function used by all other functions in this section to add a session running ansible-test.
It assumes that the command run uses Docker isolation, and thus only needs one Python version - preferably one available locally - to run.

It accepts the following parameters:

* `name: str` (**required**):
  The name of the session.

* `description: str | None` (**required**):
  The session's description.
  Will be shown when running `nox --list`.

* `extra_deps_files: list[str | os.PathLike] | None` (default: `None`):
  Additional collection dependency files to read and ensure that these collections (and their dependencies) are present.
  For example, `["tests/integration/requirements.yml"]`.

* `ansible_test_params: list[str]` (**required**):
  The parameters to pass to `ansible-test`.
  For example, `["integration", "--docker", "ubuntu2404", "-v", "--color"]`.

* `add_posargs: bool` (default `True`):
  Whether to append positional arguments provided to `nox` to the `ansible-test` command.

* `default: bool` (**required**):
  Whether the session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `ansible_core_version: str | AnsibleCoreVersion` (**required**):
  The ansible-core version to install. Can be a version string like `"2.18"`, or one of the special identifiers `"devel"` and `"milestone"`.

* `ansible_core_source: t.Literal["git", "pypi"]` (default `"git"`):
  The source where to install ansible-core from.
  For `"devel"` and `"milestone"`, always `git` will be used.

* `ansible_core_repo_name: str | None` (default `None`):
  Allows to override the repository name when `ansible_core_source == "git"`.
  By default `"ansible/ansible"` or `"ansible-community/eol-ansible"` are used, depending on `ansible_core_version`.

* `ansible_core_branch_name: str | None` (default `None`):
  Allows to override the branch name when `ansible_core_source == "git"`.

* `handle_coverage: t.Literal["never", "always", "auto"]` (default: `"auto"`):
  Whether to run `ansible-test coverage xml` after running the `ansible-test` command.
  If set to `"auto"`, will check whether `--coverage` was passed to `ansible-test`.

* `register_name: str | None` (default: `None`):
  Register session under this name.
  Should be one of `"sanity"`, `"units"`, and `"integration"`.
  It will then appear under that name for `antsibull_nox.add_matrix_generator()`.

* `register_extra_data: dict[str, t.Any] | None` (default: `None`):
  Supply additional data when registering a session.
  Values that are used by the shared workflow are `display-name` (shown to the user) and `gha-container` (used for `runs-on`).

* `callback_before: Callable[[], None] | None` (default `None`):
  Callback that will be run before `ansible-test` is run in the temporary directory.
  Can be used to set-up files like `tests/integration/integration_config.yml`.

* `callback_after: Callable[[], None] | None` (default `None`):
  Callback that will be run after `ansible-test` is run in the temporary directory.

### Example code

This adds a session called `ansible-test-integration-devel-ubuntu2404` that runs integration tests with ansible-core's development branch using its Ubuntu 24.04 container.

```python
antsibull_nox.add_ansible_test_session(
    name="ansible-test-integration-devel-ubuntu2404",
    description="Run Ubuntu 24.04 integration tests with ansible-core devel",
    extra_deps_files=["tests/integration/requirements.yml"],
    ansible_test_params=["integration", "--docker", "ubuntu2404", "-v", "--color"],
    default=False,
    ansible_core_version="devel",
    register_name="integration",
)
```
