==================================
Antsibull Nox Helper Release Notes
==================================

.. contents:: Topics

v0.7.0
======

Release Summary
---------------

Feature release.

Minor Changes
-------------

- Antsibull-nox's ansible-core ``devel`` and ``milestone`` branch versions have been updated to 2.20. This means that ``stable-2.19`` will now be added to CI matrices if ``max_version`` has not been explicitly specified (https://github.com/ansible-community/antsibull-nox/pull/91).
- The ``docs-check`` session now also passes the new ``--check-extra-docs-refs`` parameter to ``antsibull-docs lint-collection-docs`` for antsibull-docs >= 2.18.0 (https://github.com/ansible-community/antsibull-nox/pull/90).

v0.6.0
======

Release Summary
---------------

Bugfix and feature release.

Minor Changes
-------------

- Add new extra check ``no-trailing-whitespace`` (https://github.com/ansible-community/antsibull-nox/pull/85).
- Add new options to ``docs-check`` that allow to validate code blocks in collection extra docs (https://github.com/ansible-community/antsibull-nox/pull/88).
- Support running ``ruff check --fix --select ...`` in the ``formatters`` session by setting ``run_ruff_autofix=true`` in the config (https://github.com/ansible-community/antsibull-nox/issues/70, https://github.com/ansible-community/antsibull-nox/pull/82).
- Support running ``ruff check`` in the ``codeqa`` session by setting ``run_ruff_check=true`` in the config (https://github.com/ansible-community/antsibull-nox/issues/70, https://github.com/ansible-community/antsibull-nox/pull/82).
- Support running ``ruff format`` in the ``formatters`` session by setting ``run_ruff_format=true`` in the config (https://github.com/ansible-community/antsibull-nox/issues/70, https://github.com/ansible-community/antsibull-nox/pull/82).
- The ``yamllint`` test now also checks YAML and YAML+Jinja code blocks in extra documentation (``.rst`` files in ``docs/docsite/rst/``) (https://github.com/ansible-community/antsibull-nox/pull/87).

Bugfixes
--------

- Do not fail if an unexpected action group is found that only contains a metadata entry (https://github.com/ansible-community/antsibull-nox/pull/81).
- Fix config file types for ``no_unwanted_files_skip_directories`` and ``no_unwanted_files_yaml_directories`` to what is documented; that is, do not allow ``None`` (https://github.com/ansible-community/antsibull-nox/pull/85).
- Ignore metadata entries in action groups (https://github.com/ansible-community/antsibull-nox/pull/81).
- The ``no_unwanted_files_skip_directories`` option for the ``no-unwanted-files`` was not used (https://github.com/ansible-community/antsibull-nox/pull/85).

v0.5.0
======

Release Summary
---------------

Feature and bugfix release.

Minor Changes
-------------

- Allow to pass environment variables as Ansible variables for integration tests with the new ``ansible_vars_from_env_vars`` option for ``sessions.ansible_test_integration_w_default_container`` (https://github.com/ansible-community/antsibull-nox/pull/78).

Bugfixes
--------

- Fix action group test. No errors were reported due to a bug in the test (https://github.com/ansible-community/antsibull-nox/pull/80).

v0.4.0
======

Release Summary
---------------

Feature and bugfix release.

Major Changes
-------------

- Required collections can now be installed from different sources per depending on the ansible-core version (https://github.com/ansible-community/antsibull-nox/pull/76).

Minor Changes
-------------

- Capture mypy and pylint errors to report paths of files relative to collection's root, instead of relative to the virtual ``ansible_collections`` directory (https://github.com/ansible-community/antsibull-nox/pull/75).
- Make yamllint plugin check also check doc fragments (https://github.com/ansible-community/antsibull-nox/pull/73).
- Positional arguments passed to nox are now forwarded to ``ansible-lint`` (https://github.com/ansible-community/antsibull-nox/pull/74).
- The yamllint session now ignores ``RETURN`` documentation with values ``#`` and `` # `` (https://github.com/ansible-community/antsibull-nox/pull/71).
- The yamllint test no longer shows all filenames in the command line (https://github.com/ansible-community/antsibull-nox/pull/72).

Bugfixes
--------

- Adjust yamllint test to no longer use the user's global config, but only the project's config (https://github.com/ansible-community/antsibull-nox/pull/72).

v0.3.0
======

Release Summary
---------------

Feature release that is stabilizing the API.

All noxfiles and configs using this version should still work with antsibull-nox 1.0.0,
unless a critical problem is found that cannot be solved in any other way.

Minor Changes
-------------

- Add ``antsibull-nox init`` command that creates a ``noxfile.py`` and ``antsibull-nox.tomll`` to get started (https://github.com/ansible-community/antsibull-nox/pull/58).
- Add ``callback_before`` and ``callback_after`` parameters to ``antsibull_nox.add_ansible_test_session()`` (https://github.com/ansible-community/antsibull-nox/pull/63).
- Add a ``antsibull-nox`` CLI tool with a subcommand ``lint-config`` that lints ``noxfile.py`` and the ``antsibull-nox.toml`` config file (https://github.com/ansible-community/antsibull-nox/pull/56).
- Add a session for linting the antsibull-nox configuration to ``lint`` (https://github.com/ansible-community/antsibull-nox/pull/56).
- Add new options ``skip_tests``, ``allow_disabled``, and ``enable_optional_errors`` for ansible-test sanity sessions (https://github.com/ansible-community/antsibull-nox/pull/61).
- Allow to disable coverage upload for specific integration test jobs in shared workflow with ``has-coverage=false`` in extra data (https://github.com/ansible-community/antsibull-nox/pull/64).
- Ensure that Galaxy importer's output is actually collapsed on GHA (https://github.com/ansible-community/antsibull-nox/pull/67).
- Never show Galaxy importer output unless it can be collapsed, verbosity is enabled, or a new config option ``galaxy_importer_always_show_logs`` is set to ``true`` (https://github.com/ansible-community/antsibull-nox/pull/67).
- Skip symlinks that do not point to files in ``license-check`` and ``yamllint`` sessions (https://github.com/ansible-community/antsibull-nox/pull/61).
- Update shared workflow to use a ``display-name`` and ``gha-container`` extra data (https://github.com/ansible-community/antsibull-nox/pull/63).

Removed Features (previously deprecated)
----------------------------------------

- Removed all deprecated functions from ``antsibull_nox.**`` that generate sessions. The only functions left that are public API are ``antsibull_nox.load_antsibull_nox_toml()``, ``antsibull_nox.add_ansible_test_session()``, and ``antsibull_nox.sessions.prepare_collections()`` (https://github.com/ansible-community/antsibull-nox/pull/54).

Bugfixes
--------

- Action groups extra test no longer fails if ``action_groups`` does not exist in ``meta/runtime.yml``. It can now be used to ensure that there is no action group present in ``meta/runtime.yml`` (https://github.com/ansible-community/antsibull-nox/pull/60).
- Do not fail when trying to install an empty list of packages when ``run_reuse=false`` (https://github.com/ansible-community/antsibull-nox/pull/65).
- Make sure that ``extra_code_files`` is considered for ``black`` when ``run_black_modules=false`` (https://github.com/ansible-community/antsibull-nox/pull/59).
- Make sure to flush stdout after calling ``print()`` (https://github.com/ansible-community/antsibull-nox/pull/67).

v0.2.0
======

Release Summary
---------------

Major extension and overhaul with many breaking changes. The next minor release is expected to bring more stabilization.

Major Changes
-------------

- There is now a new function ``antsibull_nox.load_antsibull_nox_toml()`` which loads ``antsibull-nox.toml`` and creates configuration and sessions from it. Calling other functionality from ``antsibull_nox`` in ``noxfile.py`` is only necessary for creating own specialized sessions, or ansible-test sessions that cannot be created with the ``antsibull_nox.add_all_ansible_test_*_test_sessions*()`` type functions (https://github.com/ansible-community/antsibull-nox/pull/50, https://github.com/ansible-community/antsibull-nox/issues/34).

Minor Changes
-------------

- Add descriptions to generated sessions that are shown when running ``nox --list`` (https://github.com/ansible-community/antsibull-nox/pull/31).
- Add function ``add_matrix_generator`` which allows to generate matrixes for CI systems for ansible-test runs (https://github.com/ansible-community/antsibull-nox/pull/32).
- Add several new functions to add ansible-test runs (https://github.com/ansible-community/antsibull-nox/issues/5, https://github.com/ansible-community/antsibull-nox/pull/32, https://github.com/ansible-community/antsibull-nox/pull/41, https://github.com/ansible-community/antsibull-nox/pull/45).
- Add shared workflow for running ansible-test from nox and generating the CI matrix from nox as well (https://github.com/ansible-community/antsibull-nox/issues/35, https://github.com/ansible-community/antsibull-nox/pull/37, https://github.com/ansible-community/antsibull-nox/pull/38, https://github.com/ansible-community/antsibull-nox/pull/48, https://github.com/ansible-community/antsibull-nox/pull/53).
- Allow to add ``yamllint`` session to ``lint`` meta-session that checks YAML files, and YAML content embedded in plugins and sidecar docs (https://github.com/ansible-community/antsibull-nox/pull/42).
- Allow to add ansible-lint session (https://github.com/ansible-community/antsibull-nox/issues/40, https://github.com/ansible-community/antsibull-nox/pull/49).
- Allow to disable using installed collections that are not checked out next to the current one by setting the environment variable ``ANTSIBULL_NOX_IGNORE_INSTALLED_COLLECTIONS`` to ``true`` (https://github.com/ansible-community/antsibull-nox/pull/51).
- Collapse Galaxy importer's output in GitHub Actions (https://github.com/ansible-community/antsibull-nox/pull/46).
- In the GitHub Action, no longer use installed collections, but only ones that have been checked out next to the current one. This avoids using collections that come with the Ansible community package installed in the default GHA image (https://github.com/ansible-community/antsibull-nox/pull/51).
- The action allows to install additional Python versions with the new ``extra-python-versions`` option (https://github.com/ansible-community/antsibull-nox/pull/32).
- The action allows to pass extra commands after ``--`` with the new ``extra-args`` option (https://github.com/ansible-community/antsibull-nox/pull/32).
- antsibull-nox now automatically installs missing collections. It uses ``.nox/.cache`` to store the collection artifacts and the extracted collections (https://github.com/ansible-community/antsibull-nox/pull/46, https://github.com/ansible-community/antsibull-nox/pull/52, https://github.com/ansible-community/antsibull-nox/issues/7).
- pydantic is now a required Python dependency of antsibull-nox (https://github.com/ansible-community/antsibull-nox/pull/50).
- tomli is now a required Python dependency of antsibull-nox for Python versions 3.9 and 3.10 For Python 3.11+, the standard library tomllib will be used (https://github.com/ansible-community/antsibull-nox/pull/50).

Deprecated Features
-------------------

- All functions in ``antsibull_nox.**`` are deprecated except ``antsibull_nox.load_antsibull_nox_toml()``, ``antsibull_nox.add_ansible_test_session()``, and ``antsibull_nox.sessions.prepare_collections()``. The other function will still work for the next minor release, but will then be removed. Use ``antsibull-nox.toml`` and ``antsibull_nox.load_antsibull_nox_toml()`` instead (https://github.com/ansible-community/antsibull-nox/pull/50).

v0.1.0
======

Release Summary
---------------

Feature release.

Minor Changes
-------------

- A ``build-import-check`` session that builds and tries to import the collection with Galaxy Importer can be added with ``add_build_import_check()`` (https://github.com/ansible-community/antsibull-nox/issues/15, https://github.com/ansible-community/antsibull-nox/pull/17).
- A ``docs-check`` session that runs ``antsibull-docs lint-collection-docs`` can be added with ``add_docs_check()`` (https://github.com/ansible-community/antsibull-nox/issues/8, https://github.com/ansible-community/antsibull-nox/pull/14).
- A ``extra-checks`` session that runs extra checks such as ``no-unwanted-files`` or ``action-groups`` can be added with ``add_extra_checks()`` (https://github.com/ansible-community/antsibull-nox/issues/8, https://github.com/ansible-community/antsibull-nox/pull/14).
- A ``license-check`` session that runs ``reuse`` and checks for bad licenses can be added with ``add_license_check()`` (https://github.com/ansible-community/antsibull-nox/issues/8, https://github.com/ansible-community/antsibull-nox/pull/14).
- Allow to decide which sessions should be marked as default and which not (https://github.com/ansible-community/antsibull-nox/issues/18, https://github.com/ansible-community/antsibull-nox/pull/20).
- Allow to provide ``extra_code_files`` to ``add_lint_sessions()`` (https://github.com/ansible-community/antsibull-nox/pull/14).
- Check whether we're running in CI using the generic ``$CI`` enviornment variable instead of ``$GITHUB_ACTIONS``. ``$CI`` is set to ``true`` on Github Actions, Gitlab CI, and other CI systems (https://github.com/ansible-community/antsibull-nox/pull/28).
- For running pylint and mypy, copy the collection and dependent collections into a new tree. This allows the collection repository to be checked out outside an approriate tree structure, and it also allows the dependent collections to live in another tree structure, as long as ``ansible-galaxy collection list`` can find them (https://github.com/ansible-community/antsibull-nox/pull/1).
- When a collection checkout is not part of an ``ansible_collections`` tree, look for collections in adjacent directories of the form ``<namespace>.<name>`` that match the containing collection's FQCN (https://github.com/ansible-community/antsibull-nox/issues/6, https://github.com/ansible-community/antsibull-nox/pull/22).
- antsibull-nox now depends on antsibull-fileutils >= 1.2.0 (https://github.com/ansible-community/antsibull-nox/pull/1).

Breaking Changes / Porting Guide
--------------------------------

- The nox workflow now by default runs all sessions, unless restricted with the ``sessions`` parameter (https://github.com/ansible-community/antsibull-nox/pull/14).

Bugfixes
--------

- Make sure that black in CI checks formatting instead of just reformatting (https://github.com/ansible-community/antsibull-nox/pull/14).

v0.0.1
======

Release Summary
---------------

Initial alpha release.
