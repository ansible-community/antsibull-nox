<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Config file reference

This document assumes some basic familiarity with the [TOML file format](https://toml.io/en/).
You might also want to read [Getting Started](getting-started.md) first if you haven't already done so.

## Basic config file structure

The configuration must be named `antsibull-nox.toml`.
A basic `antsibull-nox.toml` looks as follows:

```toml
# Comments start with a '#', similar to YAML or Python.

[collection_sources]
# This section tells antsibull-nox how to install collections.
# We want to install community.internal_test_tools, community.general, and community.crypto
# from Git and not from Galaxy.
"community.internal_test_tools" = "git+https://github.com/ansible-collections/community.internal_test_tools.git,main"
"community.general" = "git+https://github.com/ansible-collections/community.general.git,main"
"community.crypto" = "git+https://github.com/ansible-collections/community.crypto.git,main"

[collection_sources_per_ansible.'2.16']
# This section tells antsibull-nox how to install collections for ansible-core 2.16.
# (Note that we have to quote the ansible-core version in the section name!)
#
# If a collection is not mentioned here, the above generic section will be used.
# (And if it cannot be found there, antsibull-nox will simply get it from ansible-galaxy's default source.)
#
# We want to install community.crypto from its stable-2 branch from Git
# (the main branch only works with ansible-core 2.17+).
"community.crypto" = "git+https://github.com/ansible-collections/community.crypto.git,stable-2"

[sessions]
# The sub-sections of 'sessions' configure sessions to add.
# An empty session configures a session with all its default values.
# Omitting a session means that the session is not added.

[sessions.lint]
# The lint session has several settings specified:
extra_code_files = ["update-docs-fragments.py"]
isort_config = "tests/nox-config-isort.cfg"
run_black_modules = false  # modules still support Python 2
black_config = "tests/nox-config-black.toml"
flake8_config = "tests/nox-config-flake8.ini"
pylint_rcfile = "tests/nox-config-pylint.rc"
pylint_modules_rcfile = "tests/nox-config-pylint-py2.rc"
yamllint_config = "tests/nox-config-yamllint.yml"
yamllint_config_plugins = "tests/nox-config-yamllint-plugins.yml"
yamllint_config_plugins_examples = "tests/nox-config-yamllint-plugins-examples.yml"
mypy_config = "tests/nox-config-mypy.ini"
mypy_extra_deps = [
    "dnspython",
    "types-lxml",
    "types-mock",
    "types-PyYAML",
]

[sessions.docs_check]
# The docs check session is added with almost all settings
# set to their defaults, except one:
validate_collection_refs="all"

[sessions.license_check]
# The license check session is added with default settings.

# ...
```

Make sure that your `noxfile.py` contains the `antsibull_nox.load_antsibull_nox_toml()` function call.
Otherwise `antsibull-nox.toml` will be ignored.

## Setup collection installation

By default,
antsibull-nox installs collection dependencies that are needed by using `ansible-galaxy collection download` to download them to a cache directory inside Nox's cache directory,
which is usually `.nox` inside the directory which contains `noxfile.py`.
If you prefer collections to be cloned from Git repositories instead,
you have to tell antsibull-nox how to download collections.

The section `[collection_sources]` allows to configure this:
```toml
[collection_sources]
# We want to install community.internal_test_tools and community.general
# from Git and not from Galaxy.
"community.internal_test_tools" = "git+https://github.com/ansible-collections/community.internal_test_tools.git,main"
"community.general" = "git+https://github.com/ansible-collections/community.general.git,main"

# community.dns should be installed from Galaxy:
"community.dns" = "community.dns"

# We want to limit community.crypto to < 3.0.0:
"community.dns" = "community.dns:<3.0.0"
```
The syntax used is explained in [the Ansible documentation on installation of collections from Git repositories](https://docs.ansible.com/ansible-core/devel/collections_guide/collections_installing.html#installing-a-collection-from-a-git-repository-at-the-command-line)
and [the Ansible documentation on installation of older versions of a collection](https://docs.ansible.com/ansible-core/devel/collections_guide/collections_installing.html#installing-an-older-version-of-a-collection).

### Specific collection sources per ansible-core version

Sometimes it is necessary to use different sources for different ansible-core versions.

For example, your collection might support ansible-core 2.16+.
For testing, you need a collection that you want to install from Git.
Unfortunately, the `main` branch only works with ansible-core 2.17+,
so you need to use another branch for ansible-core 2.16.

In the following example, community.crypto is such a collection.
Its `main` branch needs ansible-core 2.17+,
but its `stable-2` branch also supports ansible-core 2.16 and before.

You can tell antsibull-nox to use the `stable-2` branch with ansible-core 2.16
by adding a `[collection_sources_per_ansible.'2.16']` section (note the quotes!).
```toml
[collection_sources]
# This section tells antsibull-nox how to install collections.
# We want to install community.internal_test_tools, community.general, and community.crypto
# from Git and not from Galaxy.
"community.internal_test_tools" = "git+https://github.com/ansible-collections/community.internal_test_tools.git,main"
"community.general" = "git+https://github.com/ansible-collections/community.general.git,main"
"community.crypto" = "git+https://github.com/ansible-collections/community.crypto.git,main"

[collection_sources_per_ansible.'2.16']
# This section tells antsibull-nox how to install collections for ansible-core 2.16.
# (Note that we have to quote the ansible-core version in the section name!)
#
# If a collection is not mentioned here, the above generic section will be used.
# (And if it cannot be found there, antsibull-nox will simply get it from ansible-galaxy's default source.)
#
# We want to install community.crypto from its stable-2 branch from Git
# (the main branch only works with ansible-core 2.17+).
"community.crypto" = "git+https://github.com/ansible-collections/community.crypto.git,stable-2"
```

## Version Control System configuration

For features such as [Change Detection](change-detection.md), some information on the Version Control System (VCS) system needs to be known.
This can be configured in `[vcs]`.
The following options are available:

* `vcs: "git"` (**required**):
  The VCS used.
  Currently only `git` is supported.
  If you are interested in support for other VCS,
  please [create an issue](https://github.com/ansible-community/antsibull-nox/issues/new).

* `development_branch: str` (**required**):
  The name of the main development branch.
  This is usually `"main"`.

* `stable_branches: list[str]` (default: `[]`):
  A list of branches considered stable,
  like for releasing from them for older versions.
  Wildcards can be used,
  see [Python's fnmatch module](https://docs.python.org/3/library/fnmatch.html) for available wildcards.

## Package names

For many sessions, the package names of tools that are used / installed can be configured.
These options usually end with `_package`.
These options are all annotated as `PackageType` in the configuration reference below.

Some options ending with `_extra_deps` are using `list[str | SinglePackageType]`.
There, `SinglePackageType` is one single element of a `PackageType` list.

Package names may be simple strings, a special dictionary to install an
editable dependency, a requirements file, or a constraints file,
or a list of strings or such dictionaries to provide multiple of these.

Using the `ruff_package` config option as an example, the following examples
show the valid formats for specifying package names throughout the configuration:

``` toml
# Simple package name
ruff_package = "ruff"

# More verbose syntax for package name
ruff_package = {type = "package", name = "ruff"}

# Editable package (path relative to noxfile.py)
# Package will be installed without editable mode when ALLOW_EDITABLE is disabled.
ruff_package = {type = "editable", name = "./path-to-editable-package"}

# Requirements file
ruff_package = {type = "requirements", file = "requirements/ruff.txt"}

# Constraints file
# (Note that by itself, this doesn't make any sense.)
ruff_package = {type = "constraints", file = "requirements/ruff-constraints.txt"}

# A package together with a requirements file and a constraints file
ruff_package = [
  "ruff",
  {type = "requirements", file = "requirements/ruff-extra.txt"},
  {type = "constraints", file = "requirements/ruff-constraints.txt"},
]
```

!!! note
    Whether editable mode is allowed can be configured with the `ALLOW_EDITABLE` environment variable.
    Set it to `1` or `true` (ignoring case) to allow editable installs.
    If not set, the default is `true` unless `nox` is run in a CI system, in which case the default is `false`.

!!! note
    CI is currently detected by checking for the `CI` environment variable.
    If your CI system is not supported, you can simply set `CI=true` before running `nox` in CI.

## Basic linting sessions

The basic linting session, `lint`, comes with three sessions it depends on:

* `formatters`: runs `isort` and `black` to sort imports and format the code.
  During a regular run, the formatting is directly applied.
  In CI, the sorting order and formatting is checked, and the tests fail if it is not as expected.

* `codeqa`: runs `ruff check`, `flake8`, and `pylint`.

* `yamllint`: runs `yamllint` on all `.yml` and `.yaml` files, on the documentation included in Ansible modules and plugins, and on YAML code included in extra docs.

* `typing`: runs `mypy`.

These sessions can be added with the `[sessions.lint]` section in `antsibull-nox.toml`.

Which of the linters should be run can be configured
(the extra sessions are not added if they are empty),
and there are plenty of configuration settings for the indiviual formatters/linters.

### Global settings:

* `default: bool` (default `true`):
  Whether the `lint` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `extra_code_files: list[str]` (default `[]`):
  An extra list of files to run the formatters and linters on.
  By default the formatters and linters run on code files in `plugins/`, `tests/unit/`, and on `noxfile.py`.
  If you have other scripts in your collection that should be checked, you can add them with this option.

* `ruff_config: str | os.PathLike | None` (default `None`):
  Specifies a config file for `ruff`.
  Use a path relative to `noxfile.py`.
  This config file applies to all `ruff` checks
  but can be overridden for specific `ruff` invocations.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `ruff_package: PackageType` (default `"ruff"`):
  The package to install for `ruff`.
  This config file applies to all `ruff` checks
  but can be overridden for specific `ruff` invocations.
  You can specify a value here to add restrictions to the `ruff` version,
  or to pin the version,
  or to install the package from a local repository.

### `isort` (part of the `formatters` session)

* `run_isort: bool` (default `true`):
  Whether to run `isort`.

* `isort_config: str | os.PathLike | None` (default `None`):
  Specifies a config file for `isort`.
  Use a path relative to `noxfile.py`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `isort_package: PackageType` (default `"isort"`):
  The package to install for `isort` in this session.
  You can specify a value here to add restrictions to the `isort` version,
  or to pin the version,
  or to install the package from a local repository.

### `black` (part of the `formatters` session)

* `run_black: bool` (default `true`):
  Whether to run `black`.

* `run_black_modules: bool | None` (default `true`):
  Whether to run `black` also for module utils, modules, and related unit tests.
  If your collection supports Python 2.7 for modules,
  and for example needs to use the `u` prefix for Unicode strings,
  you can use this to avoid reformatting of that code (which for example removes the `u` prefix).

* `black_config: str | os.PathLike | None` (default `None`):
  Specifies a config file for `black`.
  Use a path relative to `noxfile.py`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `black_package: PackageType` (default `"black"`):
  The package to install for `black` in this session.
  You can specify a value here to add restrictions to the `black` version,
  or to pin the version,
  or to install the package from a local repository.

### `ruff format` (part of the `formatters` session)

* `run_ruff_format: bool` (default `false`):
  Whether to run `ruff format`.

* `ruff_format_config: str | os.PathLike | None` (default `None`):
  Specifies a config file for `ruff format`.
  Use a path relative to `noxfile.py`.
  Falls back to `ruff_config` if set to `None`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `ruff_format_package: PackageType | None` (default `None`):
  The package to install for `ruff` in this session.
  Falls back to `ruff_package` if set to `None`.
  You can specify a value here to add restrictions to the `ruff` version,
  or to pin the version,
  or to install the package from a local repository.

### `ruff check --fix` (part of the `formatters` session)

* `run_ruff_autofix: bool` (default `false`):
  Whether to run `ruff check --fix`.

* `ruff_autofix_config: str | os.PathLike | None` (default `None`):
  Specifies a config file for `ruff check --fix`.
  Use a path relative to `noxfile.py`.
  Falls back to `ruff_config` if set to `None`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `ruff_autofix_package: PackageType | None` (default `None`):
  The package to install for `ruff` in this session.
  Falls back to `ruff_package` if set to `None`.
  You can specify a value here to add restrictions to the `ruff` version,
  or to pin the version,
  or to install the package from a local repository.

* `ruff_autofix_select: list[str]` (default `[]`):
  Selects which rules to fix.
  Will be passed with `--select`.
  An empty list passes no `--select` option
  and runs all available fixers.

### `ruff check` (part of the `codeqa` session)

* `run_ruff_check: bool` (default `false`):
  Whether to run `ruff check`.

* `ruff_check_config: str | os.PathLike | None` (default `None`):
  Specifies a config file for `ruff check`.
  Use a path relative to `noxfile.py`.
  Falls back to `ruff_config` if set to `None`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `ruff_check_package: PackageType | None` (default `None`):
  The package to install for `ruff` in this session.
  Falls back to `ruff_package` if set to `None`.
  You can specify a value here to add restrictions to the `ruff` version,
  or to pin the version,
  or to install the package from a local repository.

### `flake8` (part of the `codeqa` session)

* `run_flake8: bool` (default `true`):
  Whether to run `flake8`.

* `flake8_config: str | os.PathLike | None` (default `None`):
  Specifies a config file for `flake8`.
  Use a path relative to `noxfile.py`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `flake8_package: PackageType` (default `"flake8"`):
  The package to install for `flake8` in this session.
  You can specify a value here to add restrictions to the `flake8` version,
  or to pin the version,
  or to install the package from a local repository.

### `pylint` (part of the `codeqa` session)

* `run_pylint: bool` (default `true`):
  Whether to run `pylint`.

* `pylint_rcfile: str | os.PathLike | None` (default `None`):
  Specifies a config file for `pylint`.
  Use a path relative to `noxfile.py`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `pylint_modules_rcfile: str | os.PathLike | None` (default `None`):
  Specifies a config file for `pylint`  for modules, module utils, and the associated unit tests.
  If not specified but `pylint_rcfile` is specified, `pylint_rcfile` will be used for these files.
  Use a path relative to `noxfile.py`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `pylint_package: PackageType` (default `"pylint"`):
  The package to install for `pylint` in this session.
  You can specify a value here to add restrictions to the `pylint` version,
  or to pin the version,
  or to install the package from a local repository.

* `pylint_ansible_core_package: PackageType` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `pylint_extra_deps: list[str | SinglePackageType]` (default `[]`):
  Specify further packages to install in this session.

    Note that currently, strings are shell splitted.
    This behavoir is deprecated and will be disallowed in a future release.
    Split these arguments up into multiple list elements,
    and/or use package type dictionaries like `{type = "requirements", file = "requirements/pylint-extra-deps.txt"}`
    depending on what you are trying to achieve.

### `yamllint` (part of the `yamllint` session)

* `run_yamllint: bool` (default `true`):
  Whether to run `yamllint`.

* `yamllint_config: str | os.PathLike | None` (default `None`):
  Specifies a config file for `yamllint`.
  Use a path relative to `noxfile.py`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `yamllint_config_plugins: str | os.PathLike | None` (default `None`):
  Specifies a config file for `yamllint` for YAML content embedded in plugins.
  Use a path relative to `noxfile.py`.

    If not provided, the same config will be used as for standalone YAML files (`yamllint_config`).

* `yamllint_config_plugins_examples: str | os.PathLike | None` (default `None`):
  Specifies a config file for `yamllint` for YAML examples embedded in plugins and sidecar docs.
  Use a path relative to `noxfile.py`.

    If not provided, the same config will be used as for YAML content embedded in plugins (`yamllint_config_plugins`),
    which falls back to the config used for standalone YAML files (`yamllint_config`).

* `yamllint_config_extra_docs: str | os.PathLike | None` (default `None`):
  Specifies a config file for `yamllint` for YAML code in extra documentation
  (`docs/docsite/rst/` directory)
  Use a path relative to `noxfile.py`.

    If not provided, the same config will be used as for YAML examples embedded in plugins (`yamllint_config_plugins_examples`),
    which falls back to the `yamllint_config_plugins` and `yamllint_config`.

* `yamllint_package: PackageType` (default `"yamllint"`):
  The package to install for `yamllint` in this session.
  You can specify a value here to add restrictions to the `yamllint` version,
  or to pin the version,
  or to install the package from a local repository.

* `yamllint_antsibull_docutils_package: PackageType` (default `"antsibull-docutils"`):
  The package to install for `antsibull-docutils` in this session.
  You can specify a value here to add restrictions to the `antsibull-docutils` version,
  or to pin the version,
  or to install the package from a local repository.

### `mypy` (part of the `typing` session)

* `run_mypy: bool` (default `true`):
  Whether to run `mypy`.

* `mypy_config: str | os.PathLike | None` (default `None`):
  Specifies a config file for `mypy`.
  Use a path relative to `noxfile.py`.
  Note that antsibull-nox does not currently supply a default config file,
  but this might change in the future.

* `mypy_package: PackageType` (default `"mypy"`):
  The package to install for `mypy` in this session.
  You can specify a value here to add restrictions to the `mypy` version,
  or to pin the version,
  or to install the package from a local repository.

* `mypy_ansible_core_package: PackageType` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `mypy_extra_deps: list[str | SinglePackageType]` (default `[]`):
  Specify further packages to install in this session.
  This can be used for typing stubs like `types-PyYAML`, `types-mock`, and so on.

    Note that currently, strings are shell splitted.
    This behavoir is deprecated and will be disallowed in a future release.
    Split these arguments up into multiple list elements,
    and/or use package type dictionaries like `{type = "requirements", file = "requirements/mypy-extra-deps.txt"}`
    depending on what you are trying to achieve.

### `antsibull-nox-config` (part of `lint` session)

* `run_antsibullnox_config_lint: bool` (default: `true`):
  Lints the antsibull-nox configuration.

### Example code

This example is from `community.dns`,
which uses explicit config files for the formatters and linters,
and does not format modules and module utils since it relies on the `u` string prefix:

It also uses a different `pylint` config for modules and module utils,
to be able to have stricter rules for the remaining code,
which is Python 3 only.

```toml
[sessions.lint]
extra_code_files = ["update-docs-fragments.py"]
isort_config = "tests/nox-config-isort.cfg"
run_black_modules = false  # modules still support Python 2
black_config = "tests/nox-config-black.toml"
flake8_config = "tests/nox-config-flake8.ini"
pylint_rcfile = "tests/nox-config-pylint.rc"
pylint_modules_rcfile = "tests/nox-config-pylint-py2.rc"
yamllint_config = "tests/nox-config-yamllint.yml"
yamllint_config_plugins = "tests/nox-config-yamllint-plugins.yml"
yamllint_config_plugins_examples = "tests/nox-config-yamllint-plugins-examples.yml"
mypy_config = "tests/nox-config-mypy.ini"
mypy_extra_deps = [
    "dnspython",
    "types-lxml",
    "types-mock",
    "types-PyYAML",
]
```

## Collection documentation check

The collection documentation check uses antsibull-docs' `antsibull-docs lint-collection-docs` command to validate various documentation-related things:

* extra documentation (`docs/docsite/extra-docs.yml`, RST files in `docs/docsite/rst/`);
* links for docsite (`docs/docsite/links.yml`);
* documentation of modules, plugins, and roles.

The latter validation of modules and plugins is more strict and validates more (and for modules, also different) aspects than the `validate-modules` test of `ansible-test sanity`.
Also `validate-modules` currently does not validate test and filter plugins, and role argument specs are not validated by it either.

The test is added with the `[sessions.docs_check]` section in `antsibull-nox.toml`, and the session is called `docs-check`.
The function has the following configuration settings:

* `default: bool` (default `true`):
  Whether the `docs-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `antsibull_docs_package: PackageType` (default `"antsibull-docs"`):
  The package to install for `antsibull-docs` in this session.
  You can specify a value here to add restrictions to the `antsibull-docs` version,
  or to pin the version,
  or to install the package from a local repository.

* `ansible_core_package: PackageType` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `validate_collection_refs: "self" | "dependent" | "all" | None` (default `None`):
  This configures whether references to content (modules/plugins/roles, their options, and return values) in module, plugins, and roles documentation should be validated.

    * If set to `self`, only references to the own collection will be checked.

    * If set to `dependent`, only references to the own collection and collections it (transitively) depends on will be checked.

    * If set to `all`, all references will be checked.
      Use `extra_collections` to specify other collections that are referenced and that are not dependencies.

    Refer to the [documentation of antsibull-docs](https://ansible.readthedocs.io/projects/antsibull-docs/collection-docs/) for more information.

* `extra_collections: list[str]` (default `[]`):
  Ensure that further collections will be added to the search path.
  This is important when setting `validate_collection_refs="all"`.

The following options are for a separate test that is run first.
It allows to apply certain restrictions to code blocks and literal blocks.

* `codeblocks_restrict_types: list[str] | None` (default `None`):
  If set to a list, only code blocks with these languages are allowed.
  To accept languages differing by case, set `codeblocks_restrict_type_exact_case` to `false`
  See `codeblocks_restrict_type_exact_case` below

* `codeblocks_restrict_type_exact_case: bool` (default `true`):
  Whether the code block languages must be exactly as in `codeblocks_restrict_types` (if set to `true`)
  or can differ by case (if set to `false`).

* `codeblocks_allow_without_type: bool` (default `true`):
  Whether code blocks without language are allowed.

* `codeblocks_allow_literal_blocks: bool` (default `true`):
  Whether literal blocks (`::`) are allowed.

* `antsibull_docutils_package: PackageType` (default `"antsibull-docutils"`):
  The package to install for `antsibull-docutils` in this session.
  You can specify a value here to add restrictions to the `antsibull-docutils` version,
  or to pin the version,
  or to install the package from a local repository.
  Note that this package is only explicitly installed when certain tests are activated.

### Example code

This example is from `community.dns`:

```toml
[sessions.docs_check]
validate_collection_refs="all"

codeblocks_restrict_types = [
    "yaml",
    "yaml+jinja",
]
codeblocks_restrict_type_exact_case = true
codeblocks_allow_without_type = false
codeblocks_allow_literal_blocks = false
```

## REUSE and license checks

If the collection conforms to the [REUSE specification](https://reuse.software/),
you can add a `license-check` session to verify conformance.

The session is added with the `[sessions.license_check]` section in `antsibull-nox.toml`, and the session is called `license-check`.
It accepts the following options:

* `default: bool` (default `true`):
  Whether the `license-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `run_reuse: bool` (default `true`):
  Whether to run `reuse lint`.

* `reuse_package: PackageType` (default `"reuse"`):
  The package to install for `reuse` in this session.
  You can specify a value here to add restrictions to the `reuse` version,
  or to pin the version,
  or to install the package from a local repository.

* `run_license_check: bool` (default `true`):
  Whether a custom check script should be run that validates the following conditions:

    1. All Python code in `plugins/` except module utils, modules, and docs fragments must be `GPL-3.0-or-later` licensed.

    2. Every non-empty file has an allowed license. (This is similar to what `reuse lint` checks.)

* `license_check_extra_ignore_paths: list[str]` (default `[]`):
  Specify more paths that are ignored.
  You can use [glob patterns](https://docs.python.org/3/library/glob.html).

### Example code

This example is from `community.dns`:

```toml
[sessions.license_check]
```

## Extra checks: action groups, unwanted files, trailing whitespace, unwanted characters/regular expressions

The extra checks session `extra-checks` runs various extra checks.
Right now it can run the following checks:

* No unwanted files:
  This check makes sure that no unwanted files are in `plugins/`.
  Which file extensions are wanted and which are not can be configured.

* Action groups:
  This check makes sure that the modules you want are part of an action group,
  and that all modules in an action group use the corresponding docs fragment.

* No trailing whitespace:
  This check flags all trailing whitespace.

* Avoid characters:
  This check allows to flag specific characters / regular expressions in files.
  For example, you can use this to flag tab characters, Windows newlines, curly quotes, and so on.

The session is added with the `[sessions.extra_checks]` section in `antsibull-nox.toml`.
It can be configured as follows:

* `default: bool` (default `true`):
  Whether the `license-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* No unwanted files:

    * `run_no_unwanted_files: bool` (default `true`):
      Whether the check should be run.

    * `no_unwanted_files_module_extensions: list[str]` (default `[".cs", ".ps1", ".psm1", ".py"]`):
      Which file extensions to accept in `plugins/modules/`.

    * `no_unwanted_files_other_extensions: list[str]` (default `[".py", ".pyi"]`):
      Which file extensions to accept in `plugins/` outside `plugins/modules/`.
      Note that YAML files can also be accepted, see the `no_unwanted_files_yaml_extensions`
      and `no_unwanted_files_yaml_directories` options.

    * `no_unwanted_files_yaml_extensions: list[str]` (default `[".yml", ".yaml"]`):
      Which file extensions to accept for YAML files.
      This is only used in directories specified by `no_unwanted_files_yaml_directories`.

    * `no_unwanted_files_skip_paths: list[str]` (default `[]`):
      Which files to ignore.

    * `no_unwanted_files_skip_directories: list[str]` (default `[]`):
      Which directories to ignore.

    * `no_unwanted_files_yaml_directories: list[str]` (default `["plugins/test/", "plugins/filter/"]`):
      In which directories YAML files should be accepted.

    * `no_unwanted_files_allow_symlinks: bool` (default `false`):
      Whether symbolic links should be accepted.

* Action groups:

    * `run_action_groups: bool` (default `false`):
      Whether the check should be run.

    * `action_groups_config: list[antsibull_nox.ActionGroup]` (default `[]`):
      The action groups to check for.
      The test makes sure that exactly these groups exist.

      Every group is an object.
      It should be defined in a new section `[[sessions.extra_checks.action_groups_config]]`.
      (See [Array of Tables](https://toml.io/en/v1.0.0#array-of-tables) in the TOML Specification.)
      Groups have the following properties:

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

      * `exclusions: list[str]` (default `[]`):
        This must list all modules whose names match `pattern`,
        but that are not part of the action group.

* No trailing whitespace:

    * `run_no_trailing_whitespace: bool` (default `false`):
      Whether the check should be run.

    * `no_trailing_whitespace_skip_paths: list[str]` (default `[]`):
      Which files to ignore.

    * `no_trailing_whitespace_skip_directories: list[str]` (default `[]`):
      Which directories to ignore.

* Avoid characters:

    * `run_avoid_characters: bool` (default `false`):
      Whether the check should be run.

    * `avoid_character_group: list[AvoidCharacterGroup]` (default `[]`):
      List of groups of regular expressions with optional names and file selectors.

      Every group is an object.
      It should be defined in a new section `[[sessions.extra_checks.avoid_character_group]]`.
      (See [Array of Tables](https://toml.io/en/v1.0.0#array-of-tables) in the TOML Specification.)
      Groups have the following properties:

      * `name: str` (**optional**):
        User-friendly name to show instead of the regular expression.

      * `regex: str` (**required**):
        A [Python regular expression](https://docs.python.org/3/library/re.html) to flag when being found.

      * `match_extensions: list[str] | None` (default `None`):
        If specified, will only match files whose filename ends with a string from this list.

      * `match_paths: list[str] | None` (default `None`):
        If specified, will only match files whose paths are part of this list.

      * `match_directories: list[str] | None` (default `None`):
        If specified, will only match files which are in a directory or subdirectory of a path in this list.

      * `skip_extensions: list[str]` (default `[]`):
        If specified, will not match files whose filename ends with a string from this list.

      * `skip_paths: list[str]` (default `[]`):
        If specified, will only match files whose paths are not part of this list.

      * `skip_directories: list[str]` (default `[]`):
        If specified, will not match files which are in a directory or subdirectory of a path in this list.

### Example code

This example is from `community.dns`.

The collection contains a data file, `plugins/public_suffix_list.dat`, that does not match any known extension.
Since this file is vendored without modifications,
and the collection conforms to the REUSE specifiation,
license information is added in another file `plugins/public_suffix_list.dat.license`.

The collection has two action groups, one for Hetzner DNS modules,
and one for Hosttech DNS modules.

```toml
[sessions.extra_checks]
run_no_unwanted_files = true
no_unwanted_files_module_extensions = [".py"]
no_unwanted_files_skip_paths = [
    "plugins/public_suffix_list.dat",
    "plugins/public_suffix_list.dat.license",
]
no_unwanted_files_yaml_extensions = [".yml"]
run_action_groups = true
run_no_trailing_whitespace = true
run_avoid_characters = true

[[sessions.extra_checks.action_groups_config]]
name = "hetzner"
pattern = "^hetzner_.*$"
exclusions = []
doc_fragment = "community.dns.attributes.actiongroup_hetzner"

[[sessions.extra_checks.action_groups_config]]
name = "hosttech"
pattern = "^hosttech_.*$"
exclusions = []
doc_fragment = "community.dns.attributes.actiongroup_hosttech"

[[sessions.extra_checks.avoid_character_group]]
name = "tab"
# Note that we have to escape the backslash for TOML.
# The actual regular expression is '\x09',
# which matches the Unicode character code 9.
regex = "\\x09"
```

## Collection build and Galaxy import test

The build and import test check whether a collection can be built with `ansible-galaxy collection build`,
and whether the resulting artefact can be imported by the Galaxy importer.

The `build-import-check` session is added with the `[sessions.build_import_check]` section in `antsibull-nox.toml`.
It accepts the following options:

* `default: bool` (default `true`):
  Whether the `build-import-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `ansible_core_package: PackageType` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `run_galaxy_importer: bool` (default `true`):
  Whether the Galaxy importer should be run on the built collection artefact.

* `galaxy_importer_package: PackageType` (default `"galaxy-importer"`):
  The package to install for `galaxy-importer` in this session.
  You can specify a value here to add restrictions to the `galaxy-importer` version,
  or to pin the version,
  or to install the package from a local repository.

* `galaxy_importer_config_path: str | None` (default `None`):
  Specifies a path to a [Galaxy importer configuration file](https://github.com/ansible/galaxy-importer#configuration).
  This allows to configure which aspects to check.
  Which settings are enabled depends on the Galaxy server the collection should be imported to.
  [Ansible Automation Hub](https://www.redhat.com/en/technologies/management/ansible/automation-hub)
  is using different settings than [Ansible Galaxy](https://galaxy.ansible.com/), for example.

* `galaxy_importer_always_show_logs : bool` (default `False`):
  Whether to always show the Galaxy importer logs.
  By default they are only shown when nox is run with verbosity enabled (`-v`)
  or when run in a CI system that supports collapsible groups,
  like GitHub Actions.

    In the latter case, the output is always shown in a collapsible group.

### Example code

This example is from `community.dns`:

```toml
[sessions.build_import_check]
run_galaxy_importer = true
```

## Run ansible-test

antsibull-nox provides several ways to run ansible-core's testing tool `ansible-test` directly from nox.
It knows which Python versions every ansible-core release supports and picks an installed version of Python for every ansible-test session if possible,
or picks the highest supported Python version for the ansible-core release is no installed Python is found.

### Add all sanity test sessions

The `ansible-test sanity` sessions are added with the `[sessions.ansible_test_sanity]` section in `antsibull-nox.toml`.
Sessions are added for all supported ansible-core versions.
Sanity tests will always be run using ansible-test's `default` container.
The function supports the following parameters:

* `default: bool` (default `false`):
  Whether the sessions should be made default.
  This means that when a user just runs `nox` without specifying sessions, these sessions will run.

* `include_devel: bool` (default `false`):
  Whether ansible-core's `devel` branch should also be used.
  This is the development version of ansible-core and can break at any moment.
  This can be very helpful to prepare your collection against breaking changes in upcoming ansible-core versions early on.
  You should only run against it if you are ready for this.

* `include_milestone: bool` (default `false`):
  Whether ansible-core's `milestone` branch should also be used.
  Note that the milestone branch is from the latest development version,
  but is updated only once for every ansible-core development phase
  at specific dates published in advance.

* `add_devel_like_branches: list[DevelLikeBranch]` (default `[]`):
  Add a list of optional repositories and branches for ansible-core
  that will be treated similar to `devel`.
  This can be used for testing ansible-core features or bugfixes
  that are still under development.
  Please note that branches are usually deleted upon merging,
  so you have to remove them again from your `noxfile.py` to avoid CI breaking.

    This option can be specified as follows:
    ```toml
    [sessions.ansible_test_sanity]
    add_devel_like_branches = [
        # To add the Data Tagging PR (https://github.com/ansible/ansible/pull/84621)
        # to CI, we can either use the special GitHub reference refs/pull/84621/head
        # to refer to the PR's HEAD:
        { branch = "refs/pull/84621/head" },

        # We can also just specify a branch as a string:
        "refs/pull/84621/head",

        # Alternatively, we can specify a GitHub repository and a branch in that
        # repository. The Data Tagging PR is based on a branch in nitzmahone's fork
        # of ansible/ansible:
        { repository = "nitzmahone/ansible", branch = "data_tagging_219" },

        # We can also provide a two-element list with repository name and branch:
        ["nitzmahone/ansible", "data_tagging_219"],
    ]
    ```

* `min_version: Version | None` (default `None`):
  If specified, will only consider ansible-core versions with that version or higher.
  This can be a string of the form `"x.y"`, specifying a minor ansible-core x.y release.

* `max_version: Version | None` (default `None`):
  If specified, will only consider ansible-core versions with that version or lower.
  This can be a string of the form `"x.y"`, specifying a minor ansible-core x.y release.

* `except_versions: list[AnsibleCoreVersion]` (default `[]`):
  If specified, will ignore ansible-core versions in this list.
  The list elements can be strings of the form `"devel"`, `"milestone"`,
  and `"x.y"` where `x` and `y` are integers that specify a minor ansible-core x.y release.

* `skip_tests: list[str]` (default `[]`):
  A list of tests to skip.

* `allow_disabled: bool` (default `false`):
  Also run tests that are disabled by default.
  Corresponds to `ansible-test sanity`'s `--allow-disabled` option.
  Beware that these tests are disabled by default for a reason.

* `enable_optional_errors: bool` (default `false`):
  Enable optional errors.
  Corresponds to `ansible-test sanity`'s `--enable-optional-errors` option.
  Beware that these errors are disabled by default for a reason.


#### Example code

This example is from `community.dns`.
It runs all sanity tests for all supported ansible-core versions,
including ansible-core's development branch.

```toml
[sessions.ansible_test_sanity]
include_devel = true
```

### Add all unit test sessions

The `ansible-test unit` sessions are added with the `[sessions.ansible_test_units]` section in `antsibull-nox.toml`.
Unit tests will always be run for all supported Python versions of the ansible-core version,
using ansible-test's `default` container.
The function supports the following parameters:

* `default: bool` (default `false`):
  Whether the sessions should be made default.
  This means that when a user just runs `nox` without specifying sessions, these sessions will run.

* `include_devel: bool` (default `false`):
  Whether ansible-core's `devel` branch should also be used.
  This is the development version of ansible-core and can break at any moment.
  This can be very helpful to prepare your collection against breaking changes in upcoming ansible-core versions early on.
  You should only run against it if you are ready for this.

* `include_milestone: bool` (default `false`):
  Whether ansible-core's `milestone` branch should also be used.
  Note that the milestone branch is from the latest development version,
  but is updated only once for every ansible-core development phase
  at specific dates published in advance.

* `add_devel_like_branches: list[DevelLikeBranch]` (default `[]`):
  Add a list of optional repositories and branches for ansible-core
  that will be treated similar to `devel`.
  This can be used for testing ansible-core features or bugfixes
  that are still under development.
  Please note that branches are usually deleted upon merging,
  so you have to remove them again from your `noxfile.py` to avoid CI breaking.

    This option can be specified as follows:
    ```toml
    [sessions.ansible_test_units]
    add_devel_like_branches = [
        # To add the Data Tagging PR (https://github.com/ansible/ansible/pull/84621)
        # to CI, we can either use the special GitHub reference refs/pull/84621/head
        # to refer to the PR's HEAD:
        { branch = "refs/pull/84621/head" },

        # We can also just specify a branch as a string:
        "refs/pull/84621/head",

        # Alternatively, we can specify a GitHub repository and a branch in that
        # repository. The Data Tagging PR is based on a branch in nitzmahone's fork
        # of ansible/ansible:
        { repository = "nitzmahone/ansible", branch = "data_tagging_219" },

        # We can also provide a two-element list with repository name and branch:
        ["nitzmahone/ansible", "data_tagging_219"],
    ]
    ```

* `min_version: Version | None` (default `None`):
  If specified, will only consider ansible-core versions with that version or higher.
  This can be a string of the form `"x.y"`, specifying a minor ansible-core x.y release.

* `max_version: Version | None` (default `None`):
  If specified, will only consider ansible-core versions with that version or lower.
  This can be a string of the form `"x.y"`, specifying a minor ansible-core x.y release.

* `except_versions: list[AnsibleCoreVersion]` (default `[]`):
  If specified, will ignore ansible-core versions in this list.
  The list elements can be strings of the form `"devel"`, `"milestone"`,
  and `"x.y"` where `x` and `y` are integers that specify a minor ansible-core x.y release.

#### Example code

This example is from `community.dns`.
It runs all unit tests for all supported ansible-core versions,
including ansible-core's development branch.

```toml
[sessions.ansible_test_units]
include_devel = true
```

### Add integration test sessions with the `default` container

The `ansible-test integration --docker default` sessions are added with the `[sessions.ansible_test_integration_w_default_container]` section in `antsibull-nox.toml`.
Sessions are added for all supported ansible-core versions.
The tests will all be run using ansible-test's `default` container.
It is possible to restrict the Python versions used to run the tests per ansible-core version.

* `default: bool` (default `false`):
  Whether the sessions should be made default.
  This means that when a user just runs `nox` without specifying sessions, these sessions will run.

* `include_devel: bool` (default `false`):
  Whether ansible-core's `devel` branch should also be used.
  This is the development version of ansible-core and can break at any moment.
  This can be very helpful to prepare your collection against breaking changes in upcoming ansible-core versions early on.
  You should only run against it if you are ready for this.

* `include_milestone: bool` (default `false`):
  Whether ansible-core's `milestone` branch should also be used.
  Note that the milestone branch is from the latest development version,
  but is updated only once for every ansible-core development phase
  at specific dates published in advance.

* `add_devel_like_branches: list[DevelLikeBranch]` (default `[]`):
  Add a list of optional repositories and branches for ansible-core
  that will be treated similar to `devel`.
  This can be used for testing ansible-core features or bugfixes
  that are still under development.
  Please note that branches are usually deleted upon merging,
  so you have to remove them again from your `noxfile.py` to avoid CI breaking.

    This option can be specified as follows:
    ```toml
    [sessions.ansible_test_integration_w_default_container]
    add_devel_like_branches = [
        # To add the Data Tagging PR (https://github.com/ansible/ansible/pull/84621)
        # to CI, we can either use the special GitHub reference refs/pull/84621/head
        # to refer to the PR's HEAD:
        { branch = "refs/pull/84621/head" },

        # We can also just specify a branch as a string:
        "refs/pull/84621/head",

        # Alternatively, we can specify a GitHub repository and a branch in that
        # repository. The Data Tagging PR is based on a branch in nitzmahone's fork
        # of ansible/ansible:
        { repository = "nitzmahone/ansible", branch = "data_tagging_219" },

        # We can also provide a two-element list with repository name and branch:
        ["nitzmahone/ansible", "data_tagging_219"],
    ]
    ```

* `min_version: Version | None` (default `None`):
  If specified, will only consider ansible-core versions with that version or higher.
  This can be a string of the form `"x.y"`, specifying a minor ansible-core x.y release.

* `max_version: Version | None` (default `None`):
  If specified, will only consider ansible-core versions with that version or lower.
  This can be a string of the form `"x.y"`, specifying a minor ansible-core x.y release.

* `except_versions: list[AnsibleCoreVersion]` (default `[]`):
  If specified, will ignore ansible-core versions in this list.
  The list elements can be strings of the form `"devel"`, `"milestone"`,
  and `"x.y"` where `x` and `y` are integers that specify a minor ansible-core x.y release.

* `core_python_versions: dict[AnsibleCoreVersion | str, list[Version]]` (default `{}`):
  Restrict the number of Python versions per ansible-core release.
  An empty list means that the ansible-core version will be skipped completely.
  If no restrictions are provided, all Python versions supported by this version of ansible-core are used;
  see `controller_python_versions_only` below for more details.

    Note that this setting is a new session `[sessions.ansible_test_integration_w_default_container.core_python_versions]`.
    The keys can be strings `"devel"`, `"milestone"`, and `"x.y"`, where ansible-core x.y is a minor ansible-core release;
    if `add_devel_like_branches`, the branch names appearing in `add_devel_like_branches` can also be specified.
    The values can be strings `"x.y"`, where Python x.y is a minor Python release.

* `controller_python_versions_only: bool` (default `false`):
  For ansible-core versions where `core_python_versions` does not provide a list of Python versions,
  usually all Python versions supported on the remote side are used.
  If this is set to `true`, only all Python versions uspported on the controller side are used.

* `ansible_vars_from_env_vars: dict[str, str]` (default `{}`):
  If given, will create an integration test config file which for every `key=value` pair,
  contains an Ansible variable `key` with the value of the environment variable `value`.
  If the environment variable is not defined, the Ansible variable will not be defined either.
  If the same variable is defined in `ansible_vars`, the value defined in `ansible_vars` will be used.

* `ansible_vars: dict[str, AnsibleValue]` (default `{}`):
  If given, will create an integration test config file which for every `key=value` pair.
  If the value is a string, number, or boolean, the value will be taken literally.
  If the value is a dictionary, it must be one of the following `type` entries:

  * `value`: specify a literal value.
    The dictionary can have the following fields:

    * `value: Any` (**required**):
      The value to store in the variable.

    * `value_template: str | None` (default `None`):
      If set, show this value insead of the real value in templates (see further below).

  * `env_var`: specify the name of an environment variable, whose value will be taken.
    The dictionary can have the following fields:

    * `name: str` (**required**):
      The name of the environment variable to use.

    * `fallback: Any` (default `""`): The value to store in the variable if the environment variable is not set.
      Will be ignored if `unset_if_not_set=true`.

    * `unset_if_not_set: bool` (default: `false`): Whether to not define the Ansible variable in case the environment variable is not set.

    * `value_template: str | None` (default `None`):
      If set, show this value insead of the real value in templates (see further below).

#### Example code

This example is from `community.dns`.

```toml
[sessions.ansible_test_integration_w_default_container]
include_devel = true

[sessions.ansible_test_integration_w_default_container.core_python_versions]
"2.14" = ["2.7", "3.5", "3.9"]
"2.15" = ["3.7"]
"2.16" = ["2.7", "3.6", "3.11"]
"2.17" = ["3.7", "3.12"]
"2.18" = ["3.8", "3.13"]
```

The following example is from `felixfontein.acme`.

```toml
[sessions.ansible_test_integration_w_default_container]
include_devel = true

[sessions.ansible_test_integration_w_default_container.ansible_vars_from_env_vars]
"github_token" = "GITHUB_TOKEN"
```

It passes the `GITHUB_TOKEN` environment variable on as `github_token`.
This allows to download files from other GitHub repositories while avoiding strict rate limiting:

```yaml
- name: Download SOPS test GPG key
  ansible.builtin.get_url:
    headers:
      Authorization: "{{ ('Bearer ' ~ github_token) if github_token is defined and github_token else '' }}"
    url: https://raw.githubusercontent.com/getsops/sops/master/pgp/sops_functional_tests_key.asc
    dest: "{{ _tempfile.path }}"
```

### Add integration test sessions by explicitly listing all sessions

The `ansible-test integration --docker` and `ansible-test integration --remote` sessions are added
with the `[sessions.ansible_test_integration]` section in `antsibull-nox.toml`.
You explicitly have to list all sessions in `antsibull-nox.toml`.

* `default: bool` (default `false`):
  Whether the sessions should be made default.
  This means that when a user just runs `nox` without specifying sessions, these sessions will run.

* `ansible_vars: dict[str, AnsibleValue]` (default `{}`):
  If given, will create an integration test config file which for every `key=value` pair.
  If the value is a string, number, or boolean, the value will be taken literally.
  If the value is a dictionary, it must be one of the following `type` entries:
  Note that this can also be specified in individual sessions.
  Variables defined there with the same name override the values defined here.

  * `value`: specify a literal value.
    The dictionary can have the following fields:

    * `value: Any` (**required**): The value to store in the variable.

  * `env_var`: specify the name of an environment variable, whose value will be taken.
    The dictionary can have the following fields:

    * `name: str` (**required**): The name of the environment variable to use.

    * `fallback: Any` (default `""`): The value to store in the variable if the environment variable is not set.
      Will be ignored if `unset_if_not_set=true`.

    * `unset_if_not_set: bool` (default: `false`): Whether to not define the Ansible variable in case the environment variable is not set.

* `session_name_template: str` (default: `"ansible-test-integration-{target_dash}{ansible_core}{dash_docker_short}{dash_remote}{dash_python_version}"`)
  The template to use for the session name.
  Formatting will be done with Python's `str.format()`.
  See below for the available variables.
  This can also be overriden for specific sessions.

* `display_name_template: str` (default: `"Ⓐ{ansible_core}{plus_py_python_version}{plus_docker_short}{plus_remote}"`)
  The template to use for the session's display name that is used in CI systems.
  Formatting will be done with Python's `str.format()`.
  See below for the available variables.
  This can also be overriden for specific sessions.

* `description_template: str` (default: `"Run integration tests with ansible-core {ansible_core}, {docker_short}{remote}"`)
  The template to use for the session's description.
  Formatting will be done with Python's `str.format()`.
  See below for the available variables.
  This can also be overriden for specific sessions.

* `tags: list[str]` (default: `[]`):
  A list of tags to add to all sessions.
  These tags can be used when filtering sessions for CI matrix generation.

* `sessions: list[SessionAnsibleTestIntegrationSession]` (default: `[]`)
  Defines session templates for ansible-test integration test sessions.

    Every session template is an object and will result in one or more sessions.
    It should be defined in a new section `[[sessions.ansible_test_integration.sessions]]`.
    (See [Array of Tables](https://toml.io/en/v1.0.0#array-of-tables) in the TOML Specification.)

    Session templates have two kind of properties.
    The first kind specifies one or more sessions by providing one or multiple values for a parameter.
    If multiple parameters are provided, one session is created for every possible combination of these parameters.
    These properties are the following:

    * `ansible_core: AnsibleCoreVersion | list[AnsibleCoreVersion]` (**required**)
      The ansible-core version to use.

    * `docker: str | list[str] | None` (default: `None`)
      The Docker image to run the tests in.
      Exactly one of `docker` and `remote` must be provided.

    * `remote: str | list[str] | None` (default: `None`)
      The remote VM to run the tests in.
      Note that ansible-test's `--remote` feature uses Ansible's CI infrastructure and requires an account.
      Exactly one of `docker` and `remote` must be provided.

    * `python_version: Version | list[Version] | None` (default: `None`)
      The Python version to run the tests with.
      This should only be provided when using the `default` Docker image,
      or when using custom Docker images that ansible-test does not know,
      or when a Docker image or remote VM offers more than one possible Python version to use.

    * `target: str | list[str] | None` (default: `None`)
      The target to run.
      This can be a string like `shippable/posix/group3/` (as used by the ansible/ansible CI),
      `azp/posix/1/` (as used in the community.general CI),
      or `gha/main/` (as used in the community.sops CI).
      Note that a trailing slash indicates a *group* of targets.
      Targets are associated to tests in the `aliases` file.

    * `gha_container: str | list[str] | None` (default: `None`)
      The `gha-container` variable.
      This is not used directly,
      but passed on through the `matrix-generator` session
      to the shared GitHub Actions workflow, for example.
      When the shared workflow is used,
      you can for example use `ubuntu-24.04-arm`
      to run tests in an ARM VM instead of the default `ubuntu-latest` x86 VM.

    The other properties allow to define common things for all sessions generated from this template.

    * `devel_like_branch: DevelLikeBranch | None` (default: `None`)
      This can only be used if `ansible_core == "devel"`.
      In that case, it allows to specify another branch from potentially another repository
      than `github.com/ansible/ansible` to use.
      This can be used for testing ansible-core features or bugfixes
      that are still under development.
      Please note that branches are usually deleted upon merging,
      so you have to remove them again from your `noxfile.py` to avoid CI breaking.

      ```toml
      # To add the Data Tagging PR (https://github.com/ansible/ansible/pull/84621)
      # to CI, we can either use the special GitHub reference refs/pull/84621/head
      # to refer to the PR's HEAD:
      devel_like_branch = { branch = "refs/pull/84621/head" }

      # We can also just specify a branch as a string:
      devel_like_branch = "refs/pull/84621/head"

      # Alternatively, we can specify a GitHub repository and a branch in that
      # repository. The Data Tagging PR is based on a branch in nitzmahone's fork
      # of ansible/ansible:
      devel_like_branch = { repository = "nitzmahone/ansible", branch = "data_tagging_219" }

      # We can also provide a two-element list with repository name and branch:
      devel_like_branch = ["nitzmahone/ansible", "data_tagging_219"]
      ```

    * `ansible_vars: dict[str, AnsibleValueField]` (default: `{}
      If given, will create an integration test config file which for every `key=value` pair.
      A key here will override a key of the same name in `[sessions.ansible_test_integration.ansible_vars]`.
      See the documentation of `[sessions.ansible_test_integration.ansible_vars]` for how to use this.

    * `session_name_template: str | None` (default: `None`)
      If given, will overwrite `[sessions.ansible_test_integration.session_name_template]`.

    * `display_name_template: str | None` (default: `None`)
      If given, will overwrite `[sessions.ansible_test_integration.display_name_template]`.

    * `description_template: str | None` (default: `None`)
      If given, will overwrite `[sessions.ansible_test_integration.description_template]`.

    * `tags: list[str]` (default: `[]`):
      A list of tags to add to all sessions for this session template.
      These tags can be used when filtering sessions for CI matrix generation.

* `groups: list[SessionAnsibleTestIntegrationGroup]` (default: `[]`)
  Defines groups of session templates for ansible-test integration test sessions.

    Groups can be used to group similar templates together by sharing some definitions.
    They also allow to create a dedicated meta session that will run all sessions created from this group.

    Every group is an object and will result in one or more sessions.
    It should be defined in a new section `[[sessions.ansible_test_integration.groups]]`.
    (See [Array of Tables](https://toml.io/en/v1.0.0#array-of-tables) in the TOML Specification.)
    Groups have the following properties:

    * `session_name: str | None` (default: `None`)
      If specified, a meta session will be created that allows to run all sessions defined within this group.

    * `description: str | None` (default: `None`)
      If `session_name` is specified, will provide the description for the meta session.
      If `description` is not specified, a generic description will be used.

    * `docker: str | list[str] | None` (default: `None`)
      Allows to provide one or more Docker images.
      This can be overridden in each session template.
    * `remote: str | list[str] | None` (default: `None`)
      Allows to provide one or more remote VM name.
      This can be overridden in each session template.
    * `python_version: Version | list[Version] | None` (default: `None`)
      Allows to provide one or more Python versions.
      This can be overridden in each session template.
    * `target: str | list[str] | None` (default: `None`)
      Allows to provide one or more target names.
      This can be overridden in each session template.
    * `gha_container: str | list[str] | None` (default: `None`)
      Allows to provide one or more GHA container names.
      This can be overridden in each session template.

    * `ansible_vars: dict[str, AnsibleValueField]` (default: `{}`)
      Allows to provide Ansible variables.
      This will override `[sessions.ansible_test_integration.ansible_vars]`,
      and will be overridden by `[sessions.ansible_test_integration.groups.sessions.ansible_vars]`.
    * `sessions: list[SessionAnsibleTestIntegrationSession]` (default: `[]`)
      A list of session templates.
      Uses the exact same format as `[sessions.ansible_test_integration.sessions]`.

    * `session_name_template: str | None` (default: `None`)
      Allows to provide a session name template that overrides the global one `[sessions.ansible_test_integration.session_name_template]`.
      This can be overridden in each session template.
    * `display_name_template: str | None` (default: `None`)
      Allows to provide a session's display name template that overrides the global one `[sessions.ansible_test_integration.display_name_template]`.
      This can be overridden in each session template.
    * `description_template: str | None` (default: `None`)
      Allows to provide a session's description template that overrides the global one `[sessions.ansible_test_integration.description_template]`.
      This can be overridden in each session template.
    * `tags: list[str]` (default: `[]`):
      A list of tags to add to all sessions for this group template.
      These tags can be used when filtering sessions for CI matrix generation.

#### Templating

The session name, display name, and description of a session are templated with Python's `str.format()`.
A list of variables that can be used is generated from a base list of variables:

* `ansible_core`: The ansible-core version.
* `docker`: The Docker image name, or empty if not provided.
* `docker_short`: A shortened Docker image name, or empty if not provided.
  The prefixes `"quay.io/ansible-community/test-image:"` and `"localhost/test-image:"` will be removed from Docker images.
* `remote`: The remote VM name, or empty if not provided.
* `python_version`: The Python version, or empty if not provided.
* `py_python_version`: The Python version prefixed by `"py"`, or empty if not provided.
* `target`: The target, or empty if not provided.
* `target_dashized`: The target with `/` replaced by `-`, and trailing `-` removed.
  Empty if no target is provided.
* `gha_container`: The value of `gha_container`, or empty if not provided.
* `gha_arm`: `"ARM"` if `gha_container` references to an ARM image.
* `gha_arm_lower`: `arm` if `gha_container` references to an ARM image.

Additionally, every variable defined for the session that is explicitly provided, or that has `template_value` set, is made available under the variable's name.

For a variable name `var` listed above, the following variables are also defined:

* `var_dash`: The content of `var` followed by a dash (`-`) if `var` is not empty, or an empty string otherwise.
* `dash_var`: The content of `var` preceeded by a dash (`-`) if `var` is not empty, or an empty string otherwise.
* `var_plus`: The content of `var` followed by a plus sign (`+`) if `var` is not empty, or an empty string otherwise.
* `plus_var`: The content of `var` preceeded by a plus sign (`+`) if `var` is not empty, or an empty string otherwise.
* `var_comma`: The content of `var` followed by a comma and space (`, `) if `var` is not empty, or an empty string otherwise.
* `comma_var`: The content of `var` preceeded by a comma and space (`, `) if `var` is not empty, or an empty string otherwise.

#### Example code

This example is a subset of the sessions defined for `community.sops`.

```toml
[sessions.ansible_test_integration]

[sessions.ansible_test_integration.ansible_vars]
github_token = { type = "env", name = "GITHUB_TOKEN", unset_if_not_set = true }

[[sessions.ansible_test_integration.groups]]
session_name = "ansible-test-integration-main"
description = "Meta-session for all ansible-test-integration-main-* sessions."
session_name_template = "ansible-test-integration-main-{ansible_core}{dash_docker_short}{dash_override_sops_version}{dash_gha_arm_lower}"
display_name_template = "main+Ⓐ{ansible_core}+SOPS-{override_sops_version}{plus_docker_short}{plus_py_python_version}{plus_gha_arm}"
description_template = "Run main integration tests with ansible-core {ansible_core}, {docker_short}, SOPS {override_sops_version}{comma_gha_arm}"
target = "gha/main/"
gha_container = "ubuntu-latest"

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "devel"
docker = ["ubuntu2204", "ubuntu2404", "fedora42"]
ansible_vars = { override_sops_version = "3.5.0" }

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "2.15"
docker = "ubuntu2004"
ansible_vars = { override_sops_version = "3.10.0" }

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "2.15"
docker = "quay.io/ansible-community/test-image:debian-bullseye"
python_version = "3.9"
ansible_vars = { override_sops_version = "latest" }

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "devel"
docker = "ubuntu2404"
gha_container = "ubuntu-24.04-arm"
ansible_vars = { override_sops_version = "latest" }

[[sessions.ansible_test_integration.groups]]
session_name = "ansible-test-integration-install-1"
description = "Meta-session for all ansible-test-integration-install-1-* sessions."
session_name_template = "ansible-test-integration-install-1-{ansible_core}{dash_docker_short}{dash_gha_arm_lower}"
display_name_template = "install-1+Ⓐ{ansible_core}{plus_docker_short}{plus_py_python_version}{plus_gha_arm}"
description_template = "Run install role integration tests (specific SOPS version) with ansible-core {ansible_core}, {docker_short}{comma_gha_arm}"
target = "gha/install/1/"
gha_container = "ubuntu-latest"

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "2.17"
docker = ["ubuntu2204", "fedora39"]

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "devel"
docker = "ubuntu2404"
gha_container = "ubuntu-24.04-arm"
ansible_vars = { github_latest_detection = "auto" }

[[sessions.ansible_test_integration.groups]]
session_name = "ansible-test-integration-install-2"
description = "Meta-session for all ansible-test-integration-install-2-* sessions."
session_name_template = "ansible-test-integration-install-2-{ansible_core}{dash_docker_short}{dash_gha_arm_lower}"
display_name_template = "install-2+Ⓐ{ansible_core}{plus_docker_short}{plus_py_python_version}{plus_gha_arm}"
description_template = "Run install role integration tests (localhost vs. remote host) with ansible-core {ansible_core}, {docker_short}{comma_gha_arm}"
target = "gha/install/2/"
gha_container = "ubuntu-latest"

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "devel"
docker = "ubuntu2204"

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "devel"
docker = "ubuntu2204"
gha_container = "ubuntu-24.04-arm"
ansible_vars = { github_latest_detection = "auto" }

[[sessions.ansible_test_integration.groups]]
session_name = "ansible-test-integration-install-3"
description = "Meta-session for all ansible-test-integration-install-3-* sessions."
session_name_template = "ansible-test-integration-install-3-{ansible_core}{dash_docker_short}{dash_gha_arm_lower}"
display_name_template = "install-3+Ⓐ{ansible_core}{plus_docker_short}{plus_py_python_version}{plus_gha_arm}"
description_template = "Run install role integration tests (latest SOPS version) with ansible-core {ansible_core}, {docker_short}{comma_gha_arm}"
target = "gha/install/3/"
gha_container = "ubuntu-latest"

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "devel"
docker = "quay.io/ansible-community/test-image:archlinux"
python_version = "3.13"
ansible_vars = { github_latest_detection = "auto" }

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "devel"
docker = "ubuntu2204"
ansible_vars = { github_latest_detection = "api" }

[[sessions.ansible_test_integration.groups.sessions]]
ansible_core = "devel"
docker = "ubuntu2404"
ansible_vars = { github_latest_detection = "latest-release" }
```

## Run ansible-lint

The [ansible-lint](https://ansible.readthedocs.io/projects/lint/) session is added with the `[sessions.ansible_lint]` section in `antsibull-nox.toml`.
The added session is called `ansible-lint`. The section can contain the following configurations:

* `default: bool` (default `true`):
  Whether the `ansible-lint` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `ansible_lint_package: PackageType` (default `"ansible-lint"`):
  The package to install for `ansible-lint` in this session.
  You can specify a value here to add restrictions to the `ansible-lint` version,
  or to pin the version,
  or to install the package from a local repository.

* `strict: bool` (default `false`):
  Whether the `--strict` parameter should be passed to ansible-lint.
  This treats warnings as errors.

It is a good idea to add
```yaml
exclude_paths:
  - .nox/
```
to your ansible-lint configuration file.
Otherwise ansible-lint might try to lint collection dependencies that antsibull-nox installed.

### Example code

This example is from `felixfontein.acme`.
It simply runs `ansible-lint`.

```toml
[sessions.ansible_lint]
```

## Execution environment check

antsibull-nox allows you to test your collection against an execution environment (EE).
The `ee-check` meta session is added with the `[sessions.ee_check]` section
or `[[sessions.ee_check.execution_environments]]` sections (one for every EE) in `antsibull-nox.toml`.
The `[sessions.ee_check]` section is optional and accepts the following options:

* `default: bool` (default `false`):
  Whether the `ee-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `ansible_builder_package: PackageType` (default `"ansible-builder"`):
  The package to install for `ansible-builder` in this session.
  You can specify a value here to add restrictions to the `ansible-builder` version,
  or to pin the version,
  or to install the package from a local repository.

* `ansible_core_package: PackageType | None` (default `None`):
  The package to install for `ansible-core` in this session.
  Note that `ansible-core` is a dependency of `ansible-runner`,
  so if not specified explicitly here it will still be installed.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `ansible_navigator_package: PackageType` (default `"ansible-navigator"`):
  The package to install for `ansible-navigator` in this session.
  You can specify a value here to add restrictions to the `ansible-navigator` version,
  or to pin the version,
  or to install the package from a local repository.

* `execution_environments: list[ExecutionEnvironmentConfig]` (**required**):
  List of execution environment configs.
  The configurations come with information on how to build the execution environment (EE) and in which ways to test them.

    Every execution environment config is an object and will result in its own session.
    (The `ee-check` meta session executes all these sessions.)
    It should be defined in a new section `[[sessions.ee_check.execution_environments]]`.
    (See [Array of Tables](https://toml.io/en/v1.0.0#array-of-tables) in the TOML Specification.)

    Every execution environment config has the following properties:

    * `name: str` (**required**):
      Specifies a unique name for the `ee-check` session.

    * `description: str | None` (default `None`):
      Adds a description for the `ee-check` session.

    * `version: 3` (default `3`):
      Configures the schema version for the EE definition.

    * `base_image_name: str` (default `"registry.fedoraproject.org/fedora-toolbox:latest"`):
      Specifies the base image to use when building the EE.
      We strongly recommend to always provide the base image explicitly (here or through `config`),
      and not to rely on this default.

    * `ansible_core_source: "package_pip" | "package_system"` (default `"package_pip"`):
      Configures the source for installing the `ansible-core` package.
      when the `ansible_core_package` option is used.

    * `ansible_core_package: PackageType | None` (default `None`):
      Specifies the name of the `ansible-core` package.

    * `ansible_runner_source: "package_pip" | "package_system"` (default `"package_pip"`):
      Configures the source for installing the `ansible-runner` package
      when the `ansible_runner_package` option is used.

    * `ansible_runner_package: PackageType | None` (default `None`):
      Specifies the name of the `ansible-runner` package.

    * `system_packages: list[str]` (default `"[]"`):
      Specifies a list of system packages to build into the EE.

    * `python_packages: list[str]` (default `"[]"`):
      Specifies a list of Python packages to build into the EE.

    * `python_interpreter_package: PackageType | None`(default `None`):
      Defines the Python system package name for the EE.

    * `python_path: str | None`(default `None`):
      Specifies the path to the Python interpreter.

    * `config: dict[str, Any]` (default `{}`):
      Allows explicit configuration of an EE definition.

        If `config` is used,
        the other options to specify values in the EE definition can still be used,
        but every value can only come from one source.
        If this is violated, an error will be produced.

        !!! warning
            The key `dependencies.galaxy` will always be overridden.

        !!! note
            antsibull-nox does not check the EE definition syntax.

    * `test_playbooks: list[str]` (**required**):
      Specifies a list of playbooks that test the collection against the EE.

    * `runtime_environment: dict[str, str]` (default `{}`):
      Specify environment variables that will be set when the playbooks are executed.
      This will be passed through `--set-environment-variable` to `ansible-navigator`.

    * `runtime_container_options: list[str]` (default `[]`):
      Specify additional options to pass to the container runtime (Podman or Docker)
      when the playbooks are executed.
      This will be passed through `--container-options` to `ansible-navigator`.

    * `runtime_extra_vars: dict[str, str]` (default `{}`):
      Specify extra variables that will be set when the playbooks are executed.
      This will be passed through `-e` to `ansible-navigator`.

For more information about these options, see the [Execution environment definition](https://ansible.readthedocs.io/projects/builder/en/latest/definition/) documentation for Ansible Builder.

!!! note
    A container engine (Docker or Podman) needs to be installed for this session.
    Information on which container engine is chosen by antsibull-nox can be found
    [on the troubleshooting page](troubleshooting.md).

### Example TOML definition

The following example shows a minimal EE check definition:

```toml
[[sessions.ee_check.execution_environments]]
name = "minimal_ee"
test_playbooks = ["tests/ee/all.yml"]
base_image_name = "registry.fedoraproject.org/fedora-toolbox:latest"
ansible_core_package = "ansible-core"
ansible_runner_package = "ansible-runner"
```

!!! note
    While the `base_image_name` option is optional, we strongly recommend to provide it explicitly,
    or alternatively provide the appropriate base image in `config`.

!!! note
    The `ansible_core_package` and `ansible_runner_package` options are necessary as the default base image `registry.fedoraproject.org/fedora-toolbox:latest` of antsibull-nox does not contain ansible-core and ansible-runner.
    ansible-builder will refuse to create the EE without both of these packages present.

The following example shows a full EE check definition:

```toml
[[sessions.ee_check.execution_environments]]
name = "fedora-toolbox"
description = "Testing EE builds with the fedora toolbox"
test_playbooks = ["tests/ee/all.yml"]
base_image_name = "registry.fedoraproject.org/fedora-toolbox:latest"
ansible_core_package = "ansible-core"
ansible_core_source = "package_pip"
ansible_runner_package = "ansible-runner"
ansible_runner_source = "package_pip"
system_packages = ["git", "curl"]
python_packages = ["jinja2", "pyyaml", "requests"]
python_interpreter_package = "python3"
python_path = "/usr/bin/python3"
```

The following example shows an explicit configuration of an EE:

```toml
[[sessions.ee_check.execution_environments]]
name = "fedora-toolbox"
description = "Testing EE builds with the fedora toolbox"
test_playbooks = ["tests/ee/all.yml"]
config.images.base_image.name = "registry.fedoraproject.org/fedora-toolbox:latest"
config.dependencies.ansible_core.package_pip = "ansible-core"
config.dependencies.ansible_runner.package_pip = "ansible-runner"
config.dependencies.system = [
    "git",
    "curl",
]
config.dependencies.python = [
    "jinja2",
    "pyyaml",
    "requests",
]
config.dependencies.python_interpreter.package_system = "python3"
config.dependencies.python_interpreter.python_path = "/usr/bin/python3"
```
