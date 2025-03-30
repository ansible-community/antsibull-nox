# Antsibull Nox Helper Release Notes

<a id="v0-1-0"></a>
## v0\.1\.0

<a id="release-summary"></a>
### Release Summary

Feature release\.

<a id="minor-changes"></a>
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

<a id="release-summary-1"></a>
### Release Summary

Initial alpha release\.
