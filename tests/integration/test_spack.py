"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from softpack_core.app import app
from softpack_core.schemas.package_collection import PackageCollection, PackageMultiVersion
from softpack_core.spack import Spack


def test_spack_packages():
    spack = Spack()
    spack.packages()

    pkgs = spack.stored_packages

    assert len(pkgs) > 1

    assert isinstance(pkgs[0], Spack.Package)

    assert pkgs[0].name != ""

    assert len(pkgs[0].versions) > 0

    assert pkgs[0].versions[0] != ""

    packages = PackageCollection.iter()

    assert len(packages) == len(pkgs)

    assert isinstance(packages[0], PackageMultiVersion)

    assert packages[0].name != ""

    assert len(packages[0].versions) != 0

    pkgs_new = Spack("spack", app.settings.spack.repo)
    pkgs_new.packages()

    assert len(pkgs_new.stored_packages) > len(pkgs)