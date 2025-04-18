# Antsibull Nox Helper Release Notes

**Topics**

- <a href="#v0-2-0">v0\.2\.0</a>
    - <a href="#release-summary">Release Summary</a>
    - <a href="#major-changes">Major Changes</a>
    - <a href="#minor-changes">Minor Changes</a>
    - <a href="#deprecated-features">Deprecated Features</a>
- <a href="#v0-1-0">v0\.1\.0</a>
    - <a href="#release-summary-1">Release Summary</a>
    - <a href="#minor-changes-1">Minor Changes</a>
    - <a href="#breaking-changes--porting-guide">Breaking Changes / Porting Guide</a>
    - <a href="#bugfixes">Bugfixes</a>
- <a href="#v0-0-1">v0\.0\.1</a>
    - <a href="#release-summary-2">Release Summary</a>

<a id="v0-2-0"></a>
## v0\.2\.0

<a id="release-summary"></a>
### Release Summary

Major extension and overhaul with many breaking changes\. The next minor release is expected to bring more stabilization\.

<a id="major-changes"></a>
### Major Changes

* There is now a new function <code>antsibull\_nox\.load\_antsibull\_nox\_toml\(\)</code> which loads <code>antsibull\-nox\.toml</code> and creates configuration and sessions from it\. Calling other functionality from <code>antsibull\_nox</code> in <code>noxfile\.py</code> is only necessary for creating own specialized sessions\, or ansible\-test sessions that cannot be created with the <code>antsibull\_nox\.add\_all\_ansible\_test\_\*\_test\_sessions\*\(\)</code> type functions \([https\://github\.com/ansible\-community/antsibull\-nox/pull/50](https\://github\.com/ansible\-community/antsibull\-nox/pull/50)\, [https\://github\.com/ansible\-community/antsibull\-nox/issues/34](https\://github\.com/ansible\-community/antsibull\-nox/issues/34)\)\.

<a id="minor-changes"></a>
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

<a id="release-summary-1"></a>
### Release Summary

Feature release\.

<a id="minor-changes-1"></a>
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

<a id="bugfixes"></a>
### Bugfixes

* Make sure that black in CI checks formatting instead of just reformatting \([https\://github\.com/ansible\-community/antsibull\-nox/pull/14](https\://github\.com/ansible\-community/antsibull\-nox/pull/14)\)\.

<a id="v0-0-1"></a>
## v0\.0\.1

<a id="release-summary-2"></a>
### Release Summary

Initial alpha release\.
