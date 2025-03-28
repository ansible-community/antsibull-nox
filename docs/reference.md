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

It also uses a different `pylint` config for modules and module utils,
to be able to have stricter rules for the remaining code,
which is Python 3 only.

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

The collection documentation check allows to use antsibull-docs' `antsibull-docs lint-collection-docs` command to validate various documentation-related things:

* extra documentation (`docs/docsite/extra-docs.yml`, RST files in `docs/docsite/rst/`);
* links for docsite (`docs/docsite/links.yml`);
* documentation of modules, plugins, and roles.

The latter validation of modules and plugins is more strict and validates more (and for modules, also different) aspects than the `validate-modules` test of `ansible-test sanity`. Also `validate-modules` currently does not validate test and filter plugins, and role argument specs are not validated by it either.

The test is added with `antsibull_nox.add_docs_check()`, and the session is called `docs-check`. The function has the following configuration settings:

* `make_docs_check_default: bool` (default `True`):
  Whether the `docs-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `antsibull_docs_package: str` (default `"antsibull-docs"`):
  The package to install for `antsibull-docs` in this session.
  You can specify a value here to add restrictions to the `antsibull-docs` version,
  or to pin the version,
  or to install the package from a local repository.

* `ansible_core_package: str` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `validate_collection_refs: t.Literal["self", "dependent", "all"] | None` (default `None`):
  This allows to configure whether references to content (modules/plugins/roles, their options, and return values) in module, plugins, and roles documentation should be validated.

    * If set to `self`, only references to the own collection will be checked.

    * If set to `dependent`, only references to the own collection and collections it (transitively) depends on will be checked.

    * If set to `all`, all references will be checked.
      Use `extra_collections` to specify other collections that are referenced and that are not dependencies.

    Refer to the [documentation of antsibull-docs](https://ansible.readthedocs.io/projects/antsibull-docs/collection-docs/) for more information.

* `extra_collections: list[str] | None` (default `None`):
  Allows to ensure that further collections will be added to the search path.
  This is important when setting `validate_collection_refs="all"`.

### Example code

This example is from `community.dns`:

```python
antsibull_nox.add_docs_check(
    validate_collection_refs="all",
)
```

## REUSE and license checks

If the collection conforms to the [REUSE specification](https://reuse.software/),
you can add a `license-check` session to verify conformance.

The `antsibull_nox.add_license_check()` function that adds this session accepts the following options:

* `make_license_check_default: bool` (default `True`):
  Whether the `license-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `run_reuse: bool` (default `True`):
  Whether to run `reuse lint`.

* `reuse_package: str` (default `"reuse"`):
  The package to install for `reuse` in this session.
  You can specify a value here to add restrictions to the `reuse` version,
  or to pin the version,
  or to install the package from a local repository.

* `run_license_check: bool` (default `True`):
  Whether a custom check script should be run that validates the following conditions:

  1. All Python code in `plugins/` except module utils, modules, and docs fragments must be `GPL-3.0-or-later` licensed.

  2. Every non-empty file has an allowed license. (This is similar to what `reuse lint` checks.)

* `license_check_extra_ignore_paths: list[str] | None` (default `None`):
  Allows to specify more paths that are ignored.
  You can use glob patterns.

### Example code

This example is from `community.dns`:

```python
antsibull_nox.add_license_check()
```

## Extra checks: action groups and unwanted files

The extra checks session `extra-checks` runs various extra checks.
Right now it can run the following checks:

* No unwanted files:
  This check makes sure that no unwanted files are in `plugins/`.
  Which file extensions are wanted and which are not can be configured.

* Action groups:
  This check makes sure that the modules you want are part of an action group,
  and that all modules in an action group use the corresponding docs fragment.

The `antsibull_nox.add_extra_checks()` function that adds this session accepts the following options:

* `make_extra_checks_default: bool` (default `True`):
  Whether the `license-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* No unwanted files:

    * `run_no_unwanted_files: bool` (default `True`):
      Whether the check should be run.

    * `no_unwanted_files_module_extensions: list[str] | None` (default `None`):
      Which file extensions to accept in `plugins/modules/`.
      The default accepts `.cs`, `.ps1`, `.psm1`, and `.py`.

    * `no_unwanted_files_other_extensions: list[str] | None` (default `None`):
      Which file extensions to accept in `plugins/` outside `plugins/modules/`.
      The default accepts `.py` and `.pyi`.
      Note that YAML files can also be accepted, see the `no_unwanted_files_yaml_extensions`
      and `no_unwanted_files_yaml_directories` options.

    * `no_unwanted_files_yaml_extensions: list[str] | None` (default `None`):
      Which file extensions to accept for YAML files.
      The default accepts `.yml` and `.yaml`.
      This is only used in directories specified by `no_unwanted_files_yaml_directories`.

    * `no_unwanted_files_skip_paths: list[str] | None` (default `None`):
      Which files to ignore.
      The default is that no file is ignored.

    * `no_unwanted_files_skip_directories: list[str] | None` (default `None`):
      Which directories to ignore.
      The default is that no directory is ignored.

    * `no_unwanted_files_yaml_directories: list[str] | None` (default `None`):
      In which directories YAML files should be accepted.
      The default is `plugins/test/` and `plugins/filter/`.

    * `no_unwanted_files_allow_symlinks: bool` (default `False`):
      Whether symbolic links should be accepted.

* Action groups:

    * `run_action_groups: bool` (default `False`):
      Whether the check should be run.

    * `action_groups_config: list[antsibull_nox.ActionGroup] | None` (default `None`):
      The action groups to check for.
      If set to `None`, the test is skipped.
      If set to a list, the test makes sure that exactly these groups exist.

      Every group is an object with the following properties:

      * `name: str` (**required**):
        The name of the action group.
        Must be equal to the name used in `meta/runtime.yml`.

      * `pattern: str` (**required**):
        A [Python regular expression](https://docs.python.org/3/library/re.html) matching
        modules that usually are part of this action group.
        Every module that is part of this action group must match this regular expression,
        otherwise the test will fail.
        If a module matching this regular expression is not part of the action group,
        it must be explicitly listed in `exclusions` (see below).

      * `doc_fragment: str` (**required**):
        The name of the documentation fragment that must be included
        exactly for all modules that are part of this action group.

      * `exclusions: list[str] | None` (default `None`):
        This must list all modules whose names match `pattern`,
        but that are not part of the action group.

### Example code

This example is from `community.dns`.

The collection contains a data file, `plugins/public_suffix_list.dat`, that does not match any known extension.
Since this file is vendored without modifications,
and the collection conforms to the REUSE specifiation,
license information is added in another file `plugins/public_suffix_list.dat.license`.

The collection has two action groups, one for Hetzner DNS modules,
and one for Hosttech DNS modules.

```python
antsibull_nox.add_extra_checks(
    run_no_unwanted_files=True,
    no_unwanted_files_module_extensions=[".py"],
    no_unwanted_files_skip_paths=[
        "plugins/public_suffix_list.dat",
        "plugins/public_suffix_list.dat.license",
    ],
    no_unwanted_files_yaml_extensions=[".yml"],
    run_action_groups=True,
    action_groups_config=[
        antsibull_nox.ActionGroup(
            name="hetzner",
            pattern="^hetzner_.*$",
            exclusions=[],
            doc_fragment="community.dns.attributes.actiongroup_hetzner",
        ),
        antsibull_nox.ActionGroup(
            name="hosttech",
            pattern="^hosttech_.*$",
            exclusions=[],
            doc_fragment="community.dns.attributes.actiongroup_hosttech",
        ),
    ],
)
```

## Collection build and Galaxy import test

The build and import test allows to test whether a collection can be built with `ansible-galaxy collection build`,
and whether the resulting artefact can be imported by the Galaxy importer.

The `antsibull_nox.add_build_import_check()` function adds the `build-import-check` session accepts the following options:

* `make_build_import_check_default: bool` (default `True`):
  Whether the `build-import-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `ansible_core_package: str` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `run_galaxy_importer: bool` (default `True`):
  Whether the Galaxy importer should be run on the built collection artefact.

* `galaxy_importer_package: str` (default `"galaxy-importer"`):
  The package to install for `galaxy-importer` in this session.
  You can specify a value here to add restrictions to the `galaxy-importer` version,
  or to pin the version,
  or to install the package from a local repository.

* `galaxy_importer_config_path: str | None` (default `None`):
  Allows to specify a path to a [Galaxy importer configuration file](https://github.com/ansible/galaxy-importer#configuration).
  This allows to configure which aspects to check.
  Which settings are enabled depends on the Galaxy server the collection should be imported to.
  [Ansible Automation Hub](https://www.redhat.com/en/technologies/management/ansible/automation-hub)
  is using different settings than [Ansible Galaxy](https://galaxy.ansible.com/), for example.

### Example code

This example is from `community.dns`:

```python
antsibull_nox.add_build_import_check(
    run_galaxy_importer=True,
)
```

## Adding own tests that need to import from the collection structure

TODO

