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
        uses: actions/checkout@v5
        with:
          persist-credentials: false
      - name: Run nox
        uses: ansible-community/antsibull-nox@main
```

!!! info
    The workflow uses the `main` branch of the `ansible-community/antsibull-nox` action.
    This is generally not a good idea, since there can be breaking changes any time.
    You can use the `stable-1` branch to get updates less often,
    but only after they have been tested on `main` for some time.

### Run extra sanity tests with change detection

While the action provided by the antsibull-nox repository allows to do change detection,
you will have to do the repository setup yourself.
If you like a simple solution, you can use a provided shared workflow for this.

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
    uses: ansible-community/antsibull-nox/.github/workflows/reusable-nox-run.yml@main
    with:
      session-name: Run extra sanity tests
      change-detection-in-prs: true
```

### Running ansible-test CI matrix from nox

If you use the `[sessions.ansible_test_sanity]`, `[sessions.ansible_test_units]`, `[sessions.ansible_test_integration_w_default_container]`, or `[sessions.ee_check]` sections in `antsibull-nox.toml`,
or the `antsibull_nox.add_ansible_test_session()` function in `noxfile.py` to add specific `ansible-test` sessions,
then you can use the shared workflow
[ansible-community/antsibull-nox/.github/workflows/reusable-nox-matrix.yml@main](https://github.com/ansible-community/antsibull-nox/blob/main/.github/workflows/reusable-nox-matrix.yml)
to generate a CI matrix and run the `ansible-test` jobs:

The following example is taken from community.dns,
with comments indicating further options:
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
      # To explicitly disable codecov upload for specific events, you can set:
      #   upload-codecov-pr: false
      #   upload-codecov-schedule: false
      #   upload-codecov-push: false
      # You can also enable change detection in PRs,
      # but that will disable codecov uploading in PRs.
      # To enable it, simply add:
      #   change-detection-in-prs: true
      # You can limit the ansible-core version with:
      #   min-ansible-core: "2.15"
      #   max-ansible-core: "2.18"
      # You can limit to all the given tags being present:
      #   include-tags: tag1, tag2, tag3
      # You can limit to all the given tags being absent:
      #   exclude-tags: tag1, tag2, tag3
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```
