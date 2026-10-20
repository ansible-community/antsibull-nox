<!--
Copyright (c) Ansible Project
GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Releasing a collection

antsibull-nox provides tools for releasing a collection. Right now, this feature is experimental.

The releaser tool can be accessed through the `antsibull-nox` CLI tool with the `antsibull-nox release` subcommand.
It can be configured in the `[releaser]` section of the [antsibull-nox.toml configuration file](config-file.md).

!!! warning
    Right now, the releaser tooling included in antsibull-nox is experimental
    and might have breaking changes in regular minor feature releases.
    Also it is right now rather restricted in scope.
    This will change in the near future.

## Configuration

The structure of the `[releaser]` section in `antsibull-nox.toml` depends on the releaser type,
which can be configured with the `type` key.
```toml
[releaser]
type = "..."
...
```

In the following sections you find information on all available releaser types.
Every releaser's documentation documents the keys allowed in its `[releaser]` section.

### Templates

Some of the strings are templates.
Generally templates can contain variables in curly brackets,
and use backslashes (`\`) to escape special characters (such as curly brackets and backspace).

* `{name}`: will be replaced by the value of the variable `name`.
  If the variable is unknown, templating will result in an error.
* `\\`: will be replaced by `\`.
* `\{`: will be replaced by `{`.
* `\}`: will be replaced by `}`.
* `\n`: will be replaced by a newline.
* `\t`: will be replaced by a tab character.

!!! example
    Template: `See {repository_url}/blob/{branch}/CHANGELOG.md for all changes.`

    Here, `{repository_url}` and `{branch}` will be replaced by the GitHub repository URL and the branch name, respectively.
    The result will be something like `See https://github.com/ansible-collections/community.crypto/blob/main/CHANGELOG.md for all changes.`.

## Zuul+GitHub releaser

The `type = "zuul+github"` releaser publishes collections to Ansible Galaxy
through the [Ansible Zuul instance](https://gateway-cloud-softwarefactory.apps.ocp.cloud.ci.centos.org/zuul/t/ansible/status)
and GitHub.

This is used for example for all `community.*` collections in the [github.com/ansible-collections organization](https://github.com/ansible-collections/).

The general workflow is as follows:

1. Create a release commit and tag it in the collection repository.
1. Push the release commit to the upstream GitHub repository.
   Wait for CI to pass.
1. Push the tag to the upstream GitHub repository.
   Zuul monitors this and will start building and publishing the release.
1. Once the release has been published to Ansible Galaxy,
   a GitHub release can be created and published.

The ``zuul+github`` releaser automates most of these steps.

### Configuration

* `type: str`:
  The releaser name.
  Must be set to `zuul+github` for this releaser.

* `code_files: "default" | list[str]` (default `"default"`):
  The code files the linters and formatters will operate on.

    If set to `"default"`, `plugins/`, `tests/unit/`, and `noxfile.py` will be used
    and the files and directories from `extra_code_files` will be added
    (for mypy and pylint, `noxfile.py` will be skipped).

Git configuration:

* `git_release_branch: str` (default `"main"`):
  The branch from which to release.
  In stable branches, change this from `main` to the branch's name.

* `git_collection_root: str` (default `"."``):
  If the collection's root (which contains `galaxy.yml`) does not coincide with the repository's root,
  this option allows to specify the path of the collection's root.

    For example, `"ansible_collections/community/foobar"` can be used
    if `galaxy.yml` can be found at `ansible_collections/community/foobar/galaxy.yml` in the repository.

* `git_tag_format: str` (default `"{version}"`):
  The format of version tags.
  The most common forms are `{version}` and `v{version}`.

    !!! note
        The Ansible Zuul instance only accepts `{version}`.

* `git_sign_commits: bool` (default `true`):
  Whether release commits should be signed.
  You need to set up commit signing in Git for this to work.

* `git_sign_tags: bool` (default `true`):
  Whether release tags should be signed.
  You need to set up tag signing in Git for this to work.

* `git_release_commit_message: str` (default `"Release {version}."`):
  The commit message for the release commit.
  This template only supports the `{version}` variable.

* `git_release_tag_message: str` (default `"{version}"`):
  The tag annotation message for the release tag.
  This template only supports the `{version}` variable.

* `git_prepare_commit_message: str` (default `"Prepare {version}."`):
  The commit message for release preparation commits.
  This template only supports the `{version}` variable.

* `git_sign_other_commits: bool | None` (default `None`):
  Whether non-release commits should be signed or not.
  If not set, the value of `git_sign_commits` will be used.

GitHub configuration:

* `github_org: str`:
  The GitHub organization.
  For example, `ansible-collections` for [github.com/ansible-collections](https://github.com/ansible-collections/).

* `github_repo: str`:
  The GitHub repository name.
  For example, `community.crypto` for [github.com/ansible-collections/community.crypto/](https://github.com/ansible-collections/community.crypto/).

* `github_upstream_remote: str` (default `"upstream"`):
  The GitHub upstream remote commonly used.
  Will be used to push the release tag to during the release process.

* `github_release_title: str`:
  The title for the GitHub release that will be created.
  This template supports the `{version}`, `{repository_url}`, `{branch}`, and `{changelog}` variables.

* `github_release_body: str`:
  The title for the GitHub release that will be created.
  This template supports the `{version}`, `{repository_url}`, `{branch}`, and `{changelog}` variables.
  The `{changelog}` variable contains the changelog for this version in MarkDown format.

Galaxy configuration:

* `galaxy_base_url: str` (default `"https://galaxy.ansible.com/api/"`):
  The Galaxy API URL.
  This will be used to look whether Zuul successfully published the release,
  and to download the release artifact and information on the release to validate the release.

Zuul configuration:

* `zuul_base_url: str`:
  The Zuul base URL.
  Example: `https://gateway-cloud-softwarefactory.apps.ocp.cloud.ci.centos.org/zuul/`

* `zuul_tenant: str`:
  The Zuul tenant name.
  Example: `ansible`

* `zuul_project_name: str`:
  The Zuul project name.
  For the Ansible Zuul instance,
  the project name usually is the GitHub organization + the repository name,
  separated by a slash (`/`).
  Example: `ansible-collections/community.crypto`

### Usage example

In this example, we assume we want to do a 3.5.1 release of the community.crypto collection.

1. Prepare the release.
   For this, we create a changelog fragment with `release_summary`,
   and modify the `version` entry of `galaxy.yml` to the value `3.5.1`.

1. Trigger the Git release.
   Run `antsibull-nox release vcs-release 3.5.1`.

    This generates the changelog, creates the release commit, and tags that commit as `3.5.1`.

1. Push the release commit to the upstream GitHub repository with `git push upstream main`
   (and `git push` to update `origin`).
   Wait for CI to pass.

    A later version of antsibull-nox might also automate this step.

1. Run `antsibull-nox release release 3.5.1 --make-latest --without-token`.

    Here, `--make-latest` will mark the release as the "latest release" on GitHub.
    You should not specify `--make-latest` when releasing versions from older stable branches.

    The parameter `--without-token` assumes that the repository is public.
    It will not provide an authorization token for any operation with GitHub.
    When creating the [GitHub release](https://github.com/ansible-collections/community.crypto/releases/tag/3.5.1),
    the "Create a release" form will be opened in the browser with most fields pre-filled.

    If you do not provide `--without-token`,
    antsibull-nox will ask you for a GitHub token when it needs one
    (at least for creating the GitHub release),
    or will read one from the `ANTSIBULL_NOX_GITHUB_TOKEN` environment variable
    (if set).

    This step will:

    1. Push the `3.5.1` tag to GitHub (`git push upstream 3.5.1`);
    1. Wait for Zuul to pick up the tag and successfully run the release job;
    1. Wait for the release to show up on Ansible Galaxy;
    1. Validate the release on Ansible Galaxy to make sure it equals the release you pushed;
    1. Create a GitHub release (as draft unless `--publish` is passed,
       respectively open the web form if no GitHub token is provided).
