==================================
Antsibull Nox Helper Release Notes
==================================

.. contents:: Topics

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
