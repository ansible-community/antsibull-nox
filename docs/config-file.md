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

## Basic linting sessions

The basic linting session, `lint`, comes with three sessions it depends on:

* `formatters`: runs `isort` and `black` to sort imports and format the code.
  During a regular run, the formatting is directly applied.
  In CI, the sorting order and formatting is checked, and the tests fail if it is not as expected.

* `codeqa`: runs `ruff check`, `flake8`, and `pylint`.

* `yamllint`: runs `yamllint` on all `.yml` and `.yaml` files, on the documentation included in Ansible modules and plugins, and on YAML code included in extra docs.

* `typing`: runs `mypy`.

!!! note
    CI is currently detected by checking for the `CI` environment variable.
    If your CI system is not supported, you can simply set `CI=true` before running `nox` in CI.

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

* `ruff_package: str` (default `"ruff"`):
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

* `isort_package: str` (default `"isort"`):
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

* `black_package: str` (default `"black"`):
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

* `ruff_format_package: str | None` (default `None`):
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

* `ruff_autofix_package: str | None` (default `None`):
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

* `ruff_check_package: str | None` (default `None`):
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

* `flake8_package: str` (default `"flake8"`):
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

* `pylint_package: str` (default `"pylint"`):
  The package to install for `pylint` in this session.
  You can specify a value here to add restrictions to the `pylint` version,
  or to pin the version,
  or to install the package from a local repository.

* `pylint_ansible_core_package: str` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `pylint_extra_deps: list[str]` (default `[]`):
  Specify further packages to install in this session.

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

* `yamllint_package: str` (default `"yamllint"`):
  The package to install for `yamllint` in this session.
  You can specify a value here to add restrictions to the `yamllint` version,
  or to pin the version,
  or to install the package from a local repository.

* `yamllint_antsibull_docutils_package: str` (default `"antsibull-docutils"`):
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

* `mypy_extra_deps: list[str]` (default `[]`):
  Specify further packages to install in this session.
  This can be used for typing stubs like `types-PyYAML`, `types-mock`, and so on.

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

* `antsibull_docutils_package: str` (default `"antsibull-docutils"`):
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

* `reuse_package: str` (default `"reuse"`):
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

## Extra checks: action groups and unwanted files

The extra checks session `extra-checks` runs various extra checks.
Right now it can run the following checks:

* No unwanted files:
  This check makes sure that no unwanted files are in `plugins/`.
  Which file extensions are wanted and which are not can be configured.

* Action groups:
  This check makes sure that the modules you want are part of an action group,
  and that all modules in an action group use the corresponding docs fragment.

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
```

## Collection build and Galaxy import test

The build and import test check whether a collection can be built with `ansible-galaxy collection build`,
and whether the resulting artefact can be imported by the Galaxy importer.

The `build-import-check` session is added with the `[sessions.build_import_check]` section in `antsibull-nox.toml`.
It accepts the following options:

* `default: bool` (default `true`):
  Whether the `build-import-check` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `ansible_core_package: str` (default `"ansible-core"`):
  The package to install for `ansible-core` in this session.
  You can specify a value here to add restrictions to the `ansible-core` version,
  or to pin the version,
  or to install the package from a local repository.

* `run_galaxy_importer: bool` (default `true`):
  Whether the Galaxy importer should be run on the built collection artefact.

* `galaxy_importer_package: str` (default `"galaxy-importer"`):
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
  Whether the session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

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
  Whether the session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

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
  Whether the session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

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

### Run ansible-lint

The [ansible-lint](https://ansible.readthedocs.io/projects/lint/) session is added with the `[sessions.ansible_lint]` section in `antsibull-nox.toml`.
The added session is called `ansible-lint`. The section can contain the following configurations:

* `default: bool` (default `true`):
  Whether the `ansible-lint` session should be made default.
  This means that when a user just runs `nox` without specifying sessions, this session will run.

* `ansible_lint_package: str` (default `"ansible-lint"`):
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

#### Example code

This example is from `felixfontein.acme`.
It simply runs `ansible-lint`.

```toml
[sessions.ansible_lint]
```
