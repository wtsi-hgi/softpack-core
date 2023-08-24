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

SoftPack Core relies on Spack. Install that first:

``` console
$ git clone -c feature.manyFiles=true --depth 1 https://github.com/spack/spack.git
$ source spack/share/spack/setup-env.sh
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

To run integration tests, you need a git repository set up with token access and
a branch named after your git repo username. Then set these environment
variables:

```
export SOFTPACK_TEST_ARTIFACTS_REPO_URL='https://[...]artifacts.git'
export SOFTPACK_TEST_ARTIFACTS_REPO_USER='username@domain'
export SOFTPACK_TEST_ARTIFACTS_REPO_TOKEN='token'
```

To run an individual test:

``` console
poetry run pytest tests/integration/artifacts.py::test_commit -sv
```

Run [MkDocs] server to view documentation:

``` console
poetry run mkdocs serve
```


[pip]: https://pip.pypa.io
[Python installation guide]: http://docs.python-guide.org/en/latest/starting/installation/
[Github repo]: https://github.com/wtsi-hgi/softpack-core
[tarball]: https://github.com/wtsi-hgi/softpack-core/tarball/master
[Poetry]: https://python-poetry.org
[Tox]: https://tox.wiki
[MkDocs]: https://www.mkdocs.org

## Credits

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [altaf-ali/cookiecutter-pypackage](https://altaf-ali.github.io/cookiecutter-pypackage) project template.

SoftPack mascot and logo courtesy of <a href="https://www.vecteezy.com/free-vector/cartoon">Cartoon Vectors by Vecteezy</a>.
