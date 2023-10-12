"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from softpack_core.spack import Spack


def test_spack_package_list():
	spack = Spack()

	packages = spack.load_collections()

	assert len(packages) == 2

	pkgs = packages[0].packages

	assert len(pkgs) > 1

	assert isinstance(pkgs[0], Spack.Package)

	assert pkgs[0].name != ""

	assert len(pkgs[0].versions) > 0

	assert pkgs[0].versions[0] != ""