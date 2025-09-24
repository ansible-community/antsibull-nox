<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Troubleshooting

Find tips and tricks for common issues.

## General problems

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

## The wrong container engine is used for certain sessions

For sessions that require a container engine, antsibull-nox tries to detect the appropriate one:

1. For execution environment sessions (`ee-check`), one of Podman or Docker is determined when the session is started.
   The behavior can be configured by the environment variable `ANTSIBULL_NOX_CONTAINER_ENGINE`.

    If set to `podman` or `docker`, that container engine will be used.
    If set to `auto`, `auto-prefer-docker`, or `auto-prefer-podman`, antsibull-nox will try to find the
    `podman` or `docker` CLI tools in the execution path and use that information to select the container engine to use.

    The default value is `auto`.

2. For ansible-test sessions, ansible-test itself detects whether to use Podman or Docker.
   By default it prefers `docker` if both `docker` and `podman` are available.
   If the environment variable `ANSIBLE_TEST_PREFER_PODMAN` is set to a non-empty value,
   it will prefer `podman` over `docker`.

    If `ANSIBLE_TEST_PREFER_PODMAN` is not set,
    but `ANTSIBULL_NOX_CONTAINER_ENGINE` is set to something other than `auto`,
    `ANSIBLE_TEST_PREFER_PODMAN` will be set to `""` (that is, prefer Docker) or `1` (that is, prefer Podman) accordingly.

## Differences between CI and local runs

If you notice that your local tests report different results than CI,
re-creating the virtual environments can also help.
Sometimes linters have newer versions with more checks that are running in CI,
while your local virtual environments are still using an older version.

## Avoid sudden CI breakages due to new versions

As a collection maintainer,
if you prefer that new tests do not suddenly appear,
you should use the `*_package` parameters to the various `antsibull.add_*()` function calls
to pin specific versions of the linters.

!!! note
    If you pin specific versions, you yourself are responsible for bumping these versions from time to time.

## Change detection does not work

1. Did you configure [the Version Control System in antsibull-nox.toml](config-file.md#version-control-system-configuration)?
1. Did you set the environment variable `ANTSIBULL_CHANGE_DETECTION` to `true`?
1. Did you set `ANTSIBULL_BASE_BRANCH` to the base branch, if it is not the main development branch of your collection?
1. Try to run `antsibull-nox show-changes` to see what change detection finds.
1. Does the test you run actually [support change detection](change-detection.md#supported-tests)?
