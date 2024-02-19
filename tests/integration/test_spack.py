"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import time

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

    packages = list(PackageCollection.iter())

    assert isinstance(packages[0], PackageMultiVersion)

    assert packages[0].name != ""

    assert len(packages[0].versions) != 0

    if app.settings.spack.repo == "https://github.com/custom-spack/repo":
        assert len(packages) == len(pkgs)
    else:
        assert len(packages) > len(pkgs)

        spack = Spack(custom_repo = app.settings.spack.repo)

        spack.packages()

        assert len(spack.stored_packages) == len(packages)


def test_spack_package_updater():
    spack = Spack()

    assert len(spack.stored_packages) == 0

    spack.keep_packages_updated(1)

    pkgs = spack.stored_packages

    assert len(pkgs) > 0

    if app.settings.spack.repo == "https://github.com/custom-spack/repo":
        pytest.skip("skipped due to missing custom repo")

    spack.custom_repo = app.settings.spack.repo

    timeout = time.time() + 60 * 2

    while True:
        new_pkgs = spack.stored_packages

        if len(new_pkgs) > len(pkgs) or time.time() > timeout:
            break

        time.sleep(0.1)

    assert len(new_pkgs) > len(pkgs)

    spack.stop_package_timer()
