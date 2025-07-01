# Antsibull Nox Helper Release Notes

<a id="v0-7-0"></a>
## v0\.7\.0

<a id="release-summary"></a>
### Release Summary

Feature release\.

<a id="minor-changes"></a>
### Minor Changes

* Antsibull\-nox\'s ansible\-core <code>devel</code> and <code>milestone</code> branch versions have been updated to 2\.20\. This means that <code>stable\-2\.19</code> will now be added to CI matrices if <code>max\_version</code> has not been explicitly specified \([https\://github\.com/ansible\-community/antsibull\-nox/pull/91](https\://github\.com/ansible\-community/antsibull\-nox/pull/91)\)\.
* The <code>docs\-check</code> session now also passes the new <code>\-\-check\-extra\-docs\-refs</code> parameter to <code>antsibull\-docs lint\-collection\-docs</code> for antsibull\-docs \>\= 2\.18\.0 \([https\://github\.com/ansible\-community/antsibull\-nox/pull/90](https\://github\.com/ansible\-community/antsibull\-nox/pull/90)\)\.

<a id="v0-6-0"></a>
## v0\.6\.0

<a id="release-summary-1"></a>
### Release Summary

Bugfix and feature release\.

<a id="minor-changes-1"></a>
### Minor Changes

* Add new extra check <code>no\-trailing\-whitespace</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/85](https\://github\.com/ansible\-community/antsibull\-nox/pull/85)\)\.
* Add new options to <code>docs\-check</code> that allow to validate code blocks in collection extra docs \([https\://github\.com/ansible\-community/antsibull\-nox/pull/88](https\://github\.com/ansible\-community/antsibull\-nox/pull/88)\)\.
* Support running <code>ruff check \-\-fix \-\-select \.\.\.</code> in the <code>formatters</code> session by setting <code>run\_ruff\_autofix\=true</code> in the config \([https\://github\.com/ansible\-community/antsibull\-nox/issues/70](https\://github\.com/ansible\-community/antsibull\-nox/issues/70)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/82](https\://github\.com/ansible\-community/antsibull\-nox/pull/82)\)\.
* Support running <code>ruff check</code> in the <code>codeqa</code> session by setting <code>run\_ruff\_check\=true</code> in the config \([https\://github\.com/ansible\-community/antsibull\-nox/issues/70](https\://github\.com/ansible\-community/antsibull\-nox/issues/70)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/82](https\://github\.com/ansible\-community/antsibull\-nox/pull/82)\)\.
* Support running <code>ruff format</code> in the <code>formatters</code> session by setting <code>run\_ruff\_format\=true</code> in the config \([https\://github\.com/ansible\-community/antsibull\-nox/issues/70](https\://github\.com/ansible\-community/antsibull\-nox/issues/70)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/82](https\://github\.com/ansible\-community/antsibull\-nox/pull/82)\)\.
* The <code>yamllint</code> test now also checks YAML and YAML\+Jinja code blocks in extra documentation \(<code>\.rst</code> files in <code>docs/docsite/rst/</code>\) \([https\://github\.com/ansible\-community/antsibull\-nox/pull/87](https\://github\.com/ansible\-community/antsibull\-nox/pull/87)\)\.

<a id="bugfixes"></a>
### Bugfixes

* Do not fail if an unexpected action group is found that only contains a metadata entry \([https\://github\.com/ansible\-community/antsibull\-nox/pull/81](https\://github\.com/ansible\-community/antsibull\-nox/pull/81)\)\.
* Fix config file types for <code>no\_unwanted\_files\_skip\_directories</code> and <code>no\_unwanted\_files\_yaml\_directories</code> to what is documented\; that is\, do not allow <code>None</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/85](https\://github\.com/ansible\-community/antsibull\-nox/pull/85)\)\.
* Ignore metadata entries in action groups \([https\://github\.com/ansible\-community/antsibull\-nox/pull/81](https\://github\.com/ansible\-community/antsibull\-nox/pull/81)\)\.
* The <code>no\_unwanted\_files\_skip\_directories</code> option for the <code>no\-unwanted\-files</code> was not used \([https\://github\.com/ansible\-community/antsibull\-nox/pull/85](https\://github\.com/ansible\-community/antsibull\-nox/pull/85)\)\.

<a id="v0-5-0"></a>
## v0\.5\.0

<a id="release-summary-2"></a>
### Release Summary

Feature and bugfix release\.

<a id="minor-changes-2"></a>
### Minor Changes

* Allow to pass environment variables as Ansible variables for integration tests with the new <code>ansible\_vars\_from\_env\_vars</code> option for <code>sessions\.ansible\_test\_integration\_w\_default\_container</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/78](https\://github\.com/ansible\-community/antsibull\-nox/pull/78)\)\.

<a id="bugfixes-1"></a>
### Bugfixes

* Fix action group test\. No errors were reported due to a bug in the test \([https\://github\.com/ansible\-community/antsibull\-nox/pull/80](https\://github\.com/ansible\-community/antsibull\-nox/pull/80)\)\.

<a id="v0-4-0"></a>
## v0\.4\.0

<a id="release-summary-3"></a>
### Release Summary

Feature and bugfix release\.

<a id="major-changes"></a>
### Major Changes

* Required collections can now be installed from different sources per depending on the ansible\-core version \([https\://github\.com/ansible\-community/antsibull\-nox/pull/76](https\://github\.com/ansible\-community/antsibull\-nox/pull/76)\)\.

<a id="minor-changes-3"></a>
### Minor Changes

* Capture mypy and pylint errors to report paths of files relative to collection\'s root\, instead of relative to the virtual <code>ansible\_collections</code> directory \([https\://github\.com/ansible\-community/antsibull\-nox/pull/75](https\://github\.com/ansible\-community/antsibull\-nox/pull/75)\)\.
* Make yamllint plugin check also check doc fragments \([https\://github\.com/ansible\-community/antsibull\-nox/pull/73](https\://github\.com/ansible\-community/antsibull\-nox/pull/73)\)\.
* Positional arguments passed to nox are now forwarded to <code>ansible\-lint</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/74](https\://github\.com/ansible\-community/antsibull\-nox/pull/74)\)\.
* The yamllint session now ignores <code>RETURN</code> documentation with values <code>\#</code> and \`\` \# \`\` \([https\://github\.com/ansible\-community/antsibull\-nox/pull/71](https\://github\.com/ansible\-community/antsibull\-nox/pull/71)\)\.
* The yamllint test no longer shows all filenames in the command line \([https\://github\.com/ansible\-community/antsibull\-nox/pull/72](https\://github\.com/ansible\-community/antsibull\-nox/pull/72)\)\.

<a id="bugfixes-2"></a>
### Bugfixes

* Adjust yamllint test to no longer use the user\'s global config\, but only the project\'s config \([https\://github\.com/ansible\-community/antsibull\-nox/pull/72](https\://github\.com/ansible\-community/antsibull\-nox/pull/72)\)\.

<a id="v0-3-0"></a>
## v0\.3\.0

<a id="release-summary-4"></a>
### Release Summary

Feature release that is stabilizing the API\.

All noxfiles and configs using this version should still work with antsibull\-nox 1\.0\.0\,
unless a critical problem is found that cannot be solved in any other way\.

<a id="minor-changes-4"></a>
### Minor Changes

* Add <code>antsibull\-nox init</code> command that creates a <code>noxfile\.py</code> and <code>antsibull\-nox\.tomll</code> to get started \([https\://github\.com/ansible\-community/antsibull\-nox/pull/58](https\://github\.com/ansible\-community/antsibull\-nox/pull/58)\)\.
* Add <code>callback\_before</code> and <code>callback\_after</code> parameters to <code>antsibull\_nox\.add\_ansible\_test\_session\(\)</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/63](https\://github\.com/ansible\-community/antsibull\-nox/pull/63)\)\.
* Add a <code>antsibull\-nox</code> CLI tool with a subcommand <code>lint\-config</code> that lints <code>noxfile\.py</code> and the <code>antsibull\-nox\.toml</code> config file \([https\://github\.com/ansible\-community/antsibull\-nox/pull/56](https\://github\.com/ansible\-community/antsibull\-nox/pull/56)\)\.
* Add a session for linting the antsibull\-nox configuration to <code>lint</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/56](https\://github\.com/ansible\-community/antsibull\-nox/pull/56)\)\.
* Add new options <code>skip\_tests</code>\, <code>allow\_disabled</code>\, and <code>enable\_optional\_errors</code> for ansible\-test sanity sessions \([https\://github\.com/ansible\-community/antsibull\-nox/pull/61](https\://github\.com/ansible\-community/antsibull\-nox/pull/61)\)\.
* Allow to disable coverage upload for specific integration test jobs in shared workflow with <code>has\-coverage\=false</code> in extra data \([https\://github\.com/ansible\-community/antsibull\-nox/pull/64](https\://github\.com/ansible\-community/antsibull\-nox/pull/64)\)\.
* Ensure that Galaxy importer\'s output is actually collapsed on GHA \([https\://github\.com/ansible\-community/antsibull\-nox/pull/67](https\://github\.com/ansible\-community/antsibull\-nox/pull/67)\)\.
* Never show Galaxy importer output unless it can be collapsed\, verbosity is enabled\, or a new config option <code>galaxy\_importer\_always\_show\_logs</code> is set to <code>true</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/67](https\://github\.com/ansible\-community/antsibull\-nox/pull/67)\)\.
* Skip symlinks that do not point to files in <code>license\-check</code> and <code>yamllint</code> sessions \([https\://github\.com/ansible\-community/antsibull\-nox/pull/61](https\://github\.com/ansible\-community/antsibull\-nox/pull/61)\)\.
* Update shared workflow to use a <code>display\-name</code> and <code>gha\-container</code> extra data \([https\://github\.com/ansible\-community/antsibull\-nox/pull/63](https\://github\.com/ansible\-community/antsibull\-nox/pull/63)\)\.

<a id="removed-features-previously-deprecated"></a>
### Removed Features \(previously deprecated\)

* Removed all deprecated functions from <code>antsibull\_nox\.\*\*</code> that generate sessions\. The only functions left that are public API are <code>antsibull\_nox\.load\_antsibull\_nox\_toml\(\)</code>\, <code>antsibull\_nox\.add\_ansible\_test\_session\(\)</code>\, and <code>antsibull\_nox\.sessions\.prepare\_collections\(\)</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/54](https\://github\.com/ansible\-community/antsibull\-nox/pull/54)\)\.

<a id="bugfixes-3"></a>
### Bugfixes

* Action groups extra test no longer fails if <code>action\_groups</code> does not exist in <code>meta/runtime\.yml</code>\. It can now be used to ensure that there is no action group present in <code>meta/runtime\.yml</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/60](https\://github\.com/ansible\-community/antsibull\-nox/pull/60)\)\.
* Do not fail when trying to install an empty list of packages when <code>run\_reuse\=false</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/65](https\://github\.com/ansible\-community/antsibull\-nox/pull/65)\)\.
* Make sure that <code>extra\_code\_files</code> is considered for <code>black</code> when <code>run\_black\_modules\=false</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/59](https\://github\.com/ansible\-community/antsibull\-nox/pull/59)\)\.
* Make sure to flush stdout after calling <code>print\(\)</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/67](https\://github\.com/ansible\-community/antsibull\-nox/pull/67)\)\.

<a id="v0-2-0"></a>
## v0\.2\.0

<a id="release-summary-5"></a>
### Release Summary

Major extension and overhaul with many breaking changes\. The next minor release is expected to bring more stabilization\.

<a id="major-changes-1"></a>
### Major Changes

* There is now a new function <code>antsibull\_nox\.load\_antsibull\_nox\_toml\(\)</code> which loads <code>antsibull\-nox\.toml</code> and creates configuration and sessions from it\. Calling other functionality from <code>antsibull\_nox</code> in <code>noxfile\.py</code> is only necessary for creating own specialized sessions\, or ansible\-test sessions that cannot be created with the <code>antsibull\_nox\.add\_all\_ansible\_test\_\*\_test\_sessions\*\(\)</code> type functions \([https\://github\.com/ansible\-community/antsibull\-nox/pull/50](https\://github\.com/ansible\-community/antsibull\-nox/pull/50)\, [https\://github\.com/ansible\-community/antsibull\-nox/issues/34](https\://github\.com/ansible\-community/antsibull\-nox/issues/34)\)\.

<a id="minor-changes-5"></a>
### Minor Changes

* Add descriptions to generated sessions that are shown when running <code>nox \-\-list</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/31](https\://github\.com/ansible\-community/antsibull\-nox/pull/31)\)\.
* Add function <code>add\_matrix\_generator</code> which allows to generate matrixes for CI systems for ansible\-test runs \([https\://github\.com/ansible\-community/antsibull\-nox/pull/32](https\://github\.com/ansible\-community/antsibull\-nox/pull/32)\)\.
* Add several new functions to add ansible\-test runs \([https\://github\.com/ansible\-community/antsibull\-nox/issues/5](https\://github\.com/ansible\-community/antsibull\-nox/issues/5)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/32](https\://github\.com/ansible\-community/antsibull\-nox/pull/32)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/41](https\://github\.com/ansible\-community/antsibull\-nox/pull/41)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/45](https\://github\.com/ansible\-community/antsibull\-nox/pull/45)\)\.
* Add shared workflow for running ansible\-test from nox and generating the CI matrix from nox as well \([https\://github\.com/ansible\-community/antsibull\-nox/issues/35](https\://github\.com/ansible\-community/antsibull\-nox/issues/35)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/37](https\://github\.com/ansible\-community/antsibull\-nox/pull/37)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/38](https\://github\.com/ansible\-community/antsibull\-nox/pull/38)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/48](https\://github\.com/ansible\-community/antsibull\-nox/pull/48)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/53](https\://github\.com/ansible\-community/antsibull\-nox/pull/53)\)\.
* Allow to add <code>yamllint</code> session to <code>lint</code> meta\-session that checks YAML files\, and YAML content embedded in plugins and sidecar docs \([https\://github\.com/ansible\-community/antsibull\-nox/pull/42](https\://github\.com/ansible\-community/antsibull\-nox/pull/42)\)\.
* Allow to add ansible\-lint session \([https\://github\.com/ansible\-community/antsibull\-nox/issues/40](https\://github\.com/ansible\-community/antsibull\-nox/issues/40)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/49](https\://github\.com/ansible\-community/antsibull\-nox/pull/49)\)\.
* Allow to disable using installed collections that are not checked out next to the current one by setting the environment variable <code>ANTSIBULL\_NOX\_IGNORE\_INSTALLED\_COLLECTIONS</code> to <code>true</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/51](https\://github\.com/ansible\-community/antsibull\-nox/pull/51)\)\.
* Collapse Galaxy importer\'s output in GitHub Actions \([https\://github\.com/ansible\-community/antsibull\-nox/pull/46](https\://github\.com/ansible\-community/antsibull\-nox/pull/46)\)\.
* In the GitHub Action\, no longer use installed collections\, but only ones that have been checked out next to the current one\. This avoids using collections that come with the Ansible community package installed in the default GHA image \([https\://github\.com/ansible\-community/antsibull\-nox/pull/51](https\://github\.com/ansible\-community/antsibull\-nox/pull/51)\)\.
* The action allows to install additional Python versions with the new <code>extra\-python\-versions</code> option \([https\://github\.com/ansible\-community/antsibull\-nox/pull/32](https\://github\.com/ansible\-community/antsibull\-nox/pull/32)\)\.
* The action allows to pass extra commands after <code>\-\-</code> with the new <code>extra\-args</code> option \([https\://github\.com/ansible\-community/antsibull\-nox/pull/32](https\://github\.com/ansible\-community/antsibull\-nox/pull/32)\)\.
* antsibull\-nox now automatically installs missing collections\. It uses <code>\.nox/\.cache</code> to store the collection artifacts and the extracted collections \([https\://github\.com/ansible\-community/antsibull\-nox/pull/46](https\://github\.com/ansible\-community/antsibull\-nox/pull/46)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/52](https\://github\.com/ansible\-community/antsibull\-nox/pull/52)\, [https\://github\.com/ansible\-community/antsibull\-nox/issues/7](https\://github\.com/ansible\-community/antsibull\-nox/issues/7)\)\.
* pydantic is now a required Python dependency of antsibull\-nox \([https\://github\.com/ansible\-community/antsibull\-nox/pull/50](https\://github\.com/ansible\-community/antsibull\-nox/pull/50)\)\.
* tomli is now a required Python dependency of antsibull\-nox for Python versions 3\.9 and 3\.10 For Python 3\.11\+\, the standard library tomllib will be used \([https\://github\.com/ansible\-community/antsibull\-nox/pull/50](https\://github\.com/ansible\-community/antsibull\-nox/pull/50)\)\.

<a id="deprecated-features"></a>
### Deprecated Features

* All functions in <code>antsibull\_nox\.\*\*</code> are deprecated except <code>antsibull\_nox\.load\_antsibull\_nox\_toml\(\)</code>\, <code>antsibull\_nox\.add\_ansible\_test\_session\(\)</code>\, and <code>antsibull\_nox\.sessions\.prepare\_collections\(\)</code>\. The other function will still work for the next minor release\, but will then be removed\. Use <code>antsibull\-nox\.toml</code> and <code>antsibull\_nox\.load\_antsibull\_nox\_toml\(\)</code> instead \([https\://github\.com/ansible\-community/antsibull\-nox/pull/50](https\://github\.com/ansible\-community/antsibull\-nox/pull/50)\)\.

<a id="v0-1-0"></a>
## v0\.1\.0

<a id="release-summary-6"></a>
### Release Summary

Feature release\.

<a id="minor-changes-6"></a>
### Minor Changes

* A <code>build\-import\-check</code> session that builds and tries to import the collection with Galaxy Importer can be added with <code>add\_build\_import\_check\(\)</code> \([https\://github\.com/ansible\-community/antsibull\-nox/issues/15](https\://github\.com/ansible\-community/antsibull\-nox/issues/15)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/17](https\://github\.com/ansible\-community/antsibull\-nox/pull/17)\)\.
* A <code>docs\-check</code> session that runs <code>antsibull\-docs lint\-collection\-docs</code> can be added with <code>add\_docs\_check\(\)</code> \([https\://github\.com/ansible\-community/antsibull\-nox/issues/8](https\://github\.com/ansible\-community/antsibull\-nox/issues/8)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/14](https\://github\.com/ansible\-community/antsibull\-nox/pull/14)\)\.
* A <code>extra\-checks</code> session that runs extra checks such as <code>no\-unwanted\-files</code> or <code>action\-groups</code> can be added with <code>add\_extra\_checks\(\)</code> \([https\://github\.com/ansible\-community/antsibull\-nox/issues/8](https\://github\.com/ansible\-community/antsibull\-nox/issues/8)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/14](https\://github\.com/ansible\-community/antsibull\-nox/pull/14)\)\.
* A <code>license\-check</code> session that runs <code>reuse</code> and checks for bad licenses can be added with <code>add\_license\_check\(\)</code> \([https\://github\.com/ansible\-community/antsibull\-nox/issues/8](https\://github\.com/ansible\-community/antsibull\-nox/issues/8)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/14](https\://github\.com/ansible\-community/antsibull\-nox/pull/14)\)\.
* Allow to decide which sessions should be marked as default and which not \([https\://github\.com/ansible\-community/antsibull\-nox/issues/18](https\://github\.com/ansible\-community/antsibull\-nox/issues/18)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/20](https\://github\.com/ansible\-community/antsibull\-nox/pull/20)\)\.
* Allow to provide <code>extra\_code\_files</code> to <code>add\_lint\_sessions\(\)</code> \([https\://github\.com/ansible\-community/antsibull\-nox/pull/14](https\://github\.com/ansible\-community/antsibull\-nox/pull/14)\)\.
* Check whether we\'re running in CI using the generic <code>\$CI</code> enviornment variable instead of <code>\$GITHUB\_ACTIONS</code>\. <code>\$CI</code> is set to <code>true</code> on Github Actions\, Gitlab CI\, and other CI systems \([https\://github\.com/ansible\-community/antsibull\-nox/pull/28](https\://github\.com/ansible\-community/antsibull\-nox/pull/28)\)\.
* For running pylint and mypy\, copy the collection and dependent collections into a new tree\. This allows the collection repository to be checked out outside an approriate tree structure\, and it also allows the dependent collections to live in another tree structure\, as long as <code>ansible\-galaxy collection list</code> can find them \([https\://github\.com/ansible\-community/antsibull\-nox/pull/1](https\://github\.com/ansible\-community/antsibull\-nox/pull/1)\)\.
* When a collection checkout is not part of an <code>ansible\_collections</code> tree\, look for collections in adjacent directories of the form <code>\<namespace\>\.\<name\></code> that match the containing collection\'s FQCN \([https\://github\.com/ansible\-community/antsibull\-nox/issues/6](https\://github\.com/ansible\-community/antsibull\-nox/issues/6)\, [https\://github\.com/ansible\-community/antsibull\-nox/pull/22](https\://github\.com/ansible\-community/antsibull\-nox/pull/22)\)\.
* antsibull\-nox now depends on antsibull\-fileutils \>\= 1\.2\.0 \([https\://github\.com/ansible\-community/antsibull\-nox/pull/1](https\://github\.com/ansible\-community/antsibull\-nox/pull/1)\)\.

<a id="breaking-changes--porting-guide"></a>
### Breaking Changes / Porting Guide

* The nox workflow now by default runs all sessions\, unless restricted with the <code>sessions</code> parameter \([https\://github\.com/ansible\-community/antsibull\-nox/pull/14](https\://github\.com/ansible\-community/antsibull\-nox/pull/14)\)\.

<a id="bugfixes-4"></a>
### Bugfixes

* Make sure that black in CI checks formatting instead of just reformatting \([https\://github\.com/ansible\-community/antsibull\-nox/pull/14](https\://github\.com/ansible\-community/antsibull\-nox/pull/14)\)\.

<a id="v0-0-1"></a>
## v0\.0\.1

<a id="release-summary-7"></a>
### Release Summary

Initial alpha release\.
