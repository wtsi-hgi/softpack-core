"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import pytest

from softpack_core.app import app
from softpack_core.schemas.package_collection import (
    PackageCollection,
    PackageMultiVersion,
)
from softpack_core.spack import Package, Spack


def test_spack_packages():
    spack = Spack()
    spack.packages()

    pkgs = spack.stored_packages

    assert len(pkgs) > 1

    assert isinstance(pkgs[0], Package)

    assert pkgs[0].name != ""

    assert len(pkgs[0].versions) > 0

    assert pkgs[0].versions[0] != ""

    packages = PackageCollection.iter()

    assert len(packages) == len(pkgs)

    assert isinstance(packages[0], PackageMultiVersion)

    assert packages[0].name != ""

    assert len(packages[0].versions) != 0

    if app.settings.spack.repo == "https://github.com/custom-spack/repo":
        pytest.skip("skipped due to missing custom repo")

    spack = Spack("spack", app.settings.spack.repo)
    spack.packages()

    assert len(spack.stored_packages) > len(pkgs)
