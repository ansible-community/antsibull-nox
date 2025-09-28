<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Change detection

Antsibull-nox allows to use change detection to run only necessary tests.
Change detection requires that you [configure the Version Control System in antsibull-nox.toml](config-file.md#version-control-system-configuration).

You can enable change detection by setting the environment variable `ANTSIBULL_CHANGE_DETECTION` to `true`.

!!! note
    Not all tests support this. Tests not supporting change detection will simply run completely.

!!! warning
    Coverage information gathered when change detection is enabled is incomplete.
    Do not enable change detection if you plan to determine coverages of PRs!

!!! note
    A quick way to see what is happening is running `antsibull-nox show-changes`.
    This will show the list of changed files that will be used to determine which tests to run on which files.
    To run `antsibull-nox show-changes`, you do not need to set `ANTSIBULL_CHANGE_DETECTION`.

## Detecting which files have been changed, and the base branch

To detect which files have been changed, antsibull-nox asks the configured VCS.
It first figures out the differences from the current branch to the configured base branch,
and then figures out the local changes that have not yet been committed,
and considers untracked files that are not ignored by the VCS.

By default, the base branch considered is the main development branch.
If that is wrong, you can explicitly configure the base branch by setting the environment variable `ANTSIBULL_BASE_BRANCH`.

!!! note
    If you invoke antsibull-nox in CI from a Pull/Merge Request and want to use change detection,
    you should set `ANTSIBULL_BASE_BRANCH` to the base branch of the MR/PR.
    All common CI systems provide ways to set `ANTSIBULL_BASE_BRANCH` accordingly.

## Supported tests

Right now, the following tests are supported:

* All ansible-test tests supported through `antsibull-nox.toml`.
* All ansible-test tests supported through `noxfile.py` that explicitly state that they allow change detection.

    !!! note
        Ansible-test only works with git.
        Additionally the collection's root directory (the directory containing `galaxy.yml` and `antsibull-nox.toml`)
        must be the repository's root (the directory containing the `.git` subdirectory).
        The latter restriction is necessary since antsibull-nox copies the repository into a temporary place
        and cannot consider directories further up.

* All `lint` sessions (`formatters`, `codeqa`, `yamllint`, `typing`).
* The `extra-checks` session and all its tests.
* All tests but `reuse` from the `license-check` session.
* The `docs-check` sessions are restricted to changed files (for code-block tests),
  or skipped if there are no appropriate changed files.
