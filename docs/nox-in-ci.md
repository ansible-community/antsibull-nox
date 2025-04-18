<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Running nox in CI

## GitHub Actions

The antsibull-nox repository contains a GitHub Action which makes it easy to run nox in GitHub's CI.
The action takes care of installing Python, nox, and antsibull-nox,
and separating environment setup from actually running the environments.

The following GitHub workflow demonstrates how the action can be used.
It is taken from the community.dns collection.
It checks out the collection in `ansible_collections/community/dns`,
installs needed collections in the same tree structure (`-p .` parameter of `ansible-galaxy collection install`),
and runs nox inside the collection checkout directory (`ansible_collections/community/dns`).

Note that you have to install the needed collections yourself,
antsibull-nox is currently not doing that for you.

```yaml
---
name: nox
'on':
  push:
    branches:
      - main
      - stable-*
  pull_request:
  # Run CI once per day (at 07:30 UTC)
  schedule:
    - cron: '30 7 * * *'
  workflow_dispatch:

jobs:
  nox:
    runs-on: ubuntu-latest
    name: "Run nox"
    steps:
      - name: Check out collection
        uses: actions/checkout@v4
        with:
          path: ansible_collections/community/dns
          persist-credentials: false
      - name: Check out dependent collections
        run: >-
          ansible-galaxy collection install -p .
          git+https://github.com/ansible-collections/community.internal_test_tools.git,main
          git+https://github.com/ansible-collections/community.library_inventory_filtering.git,stable-1
      - name: Run nox
        uses: ansible-community/antsibull-nox@main
        with:
          working-directory: ansible_collections/community/dns
```

!!! info
    The workflow uses the `main` branch of the `ansible-community/antsibull-nox` action.
    This is generally not a good idea, since there can be breaking changes any time.
    Once antsibull-nox stabilizes we will provide stable branches that you can use
    that should not introduce breaking changes.

### Running ansible-test CI matrix from nox

If you use the `[sessions.ansible_test_sanity]`, `[sessions.ansible_test_units]`, or `[sessions.ansible_test_integration_w_default_container]` sections in `antsibull-nox.toml`,
or the `antsibull_nox.add_ansible_test_session()` function in `noxfile.py` to add specific `ansible-test` sessions,
then you can use the shared workflow
[ansible-community/antsibull-nox/.github/workflows/reusable-nox-matrix.yml@main](https://github.com/ansible-community/antsibull-nox/blob/main/.github/workflows/reusable-nox-matrix.yml)
to generate a CI matrix and run the `ansible-test` jobs:

The following example is taken from community.dns:
```yaml
---
name: nox
'on':
  push:
    branches:
      - main
      - stable-*
  pull_request:
  # Run CI once per day (at 04:30 UTC)
  schedule:
    - cron: '30 4 * * *'
  workflow_dispatch:

jobs:
  ansible-test:
    uses: ansible-community/antsibull-nox/.github/workflows/reusable-nox-matrix.yml@main
    with:
      upload-codecov: true
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```
