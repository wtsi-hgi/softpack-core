# SoftPack Core


[![pypi](https://img.shields.io/pypi/v/softpack-core.svg)](https://pypi.org/project/softpack-core/)
[![python](https://img.shields.io/pypi/pyversions/softpack-core.svg)](https://pypi.org/project/softpack-core/)
[![Build Status](https://github.com/wtsi-hgi/softpack-core/actions/workflows/dev.yml/badge.svg)](https://github.com/wtsi-hgi/softpack-core/actions/workflows/dev.yml)
[![codecov](https://codecov.io/gh/wtsi-hgi/softpack-core/branch/main/graphs/badge.svg)](https://codecov.io/github/wtsi-hgi/softpack-core)
<br/>
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](https://www.contributor-covenant.org/version/2/1/code_of_conduct)



SoftPack Core - GraphQL backend service


* Documentation: <https://wtsi-hgi.github.io/softpack-core>
* GitHub: <https://github.com/wtsi-hgi/softpack-core>
* PyPI: <https://pypi.org/project/softpack-core/>
* Free software: MIT


## Features

* Provides GraphQL API for managing SoftPack environments.

## Installation

### External dependencies

SoftPack Core requires Python version 3.11 or greater.

This project also relies on Spack. Install that first:

``` console
$ git clone -c feature.manyFiles=true --depth 1 https://github.com/spack/spack.git
$ source spack/share/spack/setup-env.sh
```

To start the service, you will also need to configure a git repository to store
artifacts, and configure details of an LDAP server to query group information:

```yaml
artifacts:
  repo: # see "integration tests" below

ldap:
  server: "ldaps://ldap.example"
  base: "ou=group,dc=example,dc=ac,dc=uk"
  filter: "memberuid={user}"
  group:
    attr: "cn"
    pattern: ".*"

```

### Stable release

To install SoftPack Core, run this command in your
terminal:

``` console
$ pip install softpack-core
```

This is the preferred method to install SoftPack Core, as it will always install the most recent stable release.

If you don't have [pip][] installed, this [Python installation guide][]
can guide you through the process.

### From source

The source for SoftPack Core can be downloaded from
the [Github repo][].

You can either clone the public repository:

``` console
$ git clone https://github.com/wtsi-hgi/softpack-core.git
```

Or download the [tarball][]:

``` console
$ curl -OJL https://github.com/wtsi-hgi/softpack-core/tarball/master
```

Once you have a copy of the source, you can install it with:

``` console
$ pip install .
```

### Development

For development mode, clone the repository and use [Poetry][] to install the
package.

``` console
$ git clone https://github.com/wtsi-hgi/softpack-core.git
```

Install [Poetry][]:

``` console
$ pip install poetry
```

Install [Poetry][] environments for development:

``` console
poetry install --with dev,doc,test
```

Run tests with [Tox][]

``` console
poetry run tox
```

To run integration tests, you need:

- a git repository, hosted on e.g. GitHub or GitLab
- an access token for the git repository
  - for GitLab, this requires the "developer" role and the "write_repository" scope
  - for GitHub, this requires read-write access to repository contents
- a branch to run the tests on (must match `username` in the config below)
- the appropriate SoftPack config, described below

Make sure the artifacts/repo section of `~/.softpack/core/config.yml` is
configured correctly:

```yaml
artifacts:
  repo:
    url: https://github.com/[your-org]/development-softpack-artifacts.git # HTTPS link to the repo
    username: [your-username] # for whatever platform the repo is hosted on
    author: [your-name] # can be anything
    email: [your-email] # can be anything
    writer: [your-token] # the access token for the repo (or your password for the repo host)
```

Then enable the integration tests by suppling --repo to `poetry run pytest`, or
to tox like this:

```
poetry run tox -- -- --repo
```

To discover all tests and run them (skipping integration tests with no --repo):

``` console
poetry run pytest tests -sv
```

To run just the integration tests:

``` console
poetry run pytest tests/integration -sv --repo
```

To run an individual test:

``` console
poetry run pytest tests/integration/test_artifacts.py::test_clone -sv --repo
```

Run [MkDocs] server to view documentation:

``` console
poetry run mkdocs serve
```

To generate a GraphQL schema file:

```
poetry run strawberry export-schema softpack_core.graphql:GraphQL.schema > schema.graphql
```


[pip]: https://pip.pypa.io
[Python installation guide]: http://docs.python-guide.org/en/latest/starting/installation/
[Github repo]: https://github.com/wtsi-hgi/softpack-core
[tarball]: https://github.com/wtsi-hgi/softpack-core/tarball/master
[Poetry]: https://python-poetry.org
[Tox]: https://tox.wiki
[MkDocs]: https://www.mkdocs.org

## Configuration

The SoftPack Core configuration file is located at `~/.softpack/core/config.yml`.

The following is the schema for the settings:

```yaml
server:
  header:
    origins: list[AnyHttpUrl] # List of valid origin URLs from which the Core API can be called.
  host: str # Host on which to bind the server.
  port: int # Port on which to bind the server.

artifacts:
    path: Path # Path to store artefacts repo.
    repo:
      url: AnyUrl             # URL to artefacts repo.
      username: Optional[str] # Username required to access artefacts repo.
      author: str             # Author name for git commits to artefacts repo.
      email: str              # Email address for author of git commits to artefacts repo.
      reader: Optional[str]   # Auth token for read access to artefacts repo.
      writer: Optional[str]   # Auth token for write access to artefacts repo.
      branch: Optional[str]   # Branch to use for artefacts repo.

spack:
  repo: str            # URL to spack recipe repo.
  bin: str             # Path to spack exectable.
  cache: Optional[str] # Directory to store cached spack recipe information.

builder:
  host: str # URL to a GSB server
  port: int # Port of the GSB server

recipes:
  toAddr: Optional[str]        # Address to which recipe requests will be sent.
  fromAddr: Optional[str]      # Address from which recipe requests will be sent.
  smtp: Optional[str]          # Address to an SMTP relay
  localHostname: Optional[str] # Hostname to use for SMTP HELO.
```

## Usage

To start a server in production:

```bash
softpack-core service run
```

To run a server to test softpack-web:

```bash
softpack-core service run --branch <any-name>
```

## Credits

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [altaf-ali/cookiecutter-pypackage](https://altaf-ali.github.io/cookiecutter-pypackage) project template.

SoftPack mascot and logo courtesy of <a href="https://www.vecteezy.com/free-vector/cartoon">Cartoon Vectors by Vecteezy</a>.
