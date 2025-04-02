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
