"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import importlib
import itertools
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from uuid import UUID


class Spack:
    """Spack interface class."""

    @dataclass
    class Modules:
        """Spack modules."""

        config: ModuleType
        repo: ModuleType

    def __init__(self) -> None:
        """Constructor."""
        self.modules = self.load_modules()
        self.repos = self.load_repo_list()
        self.packages = self.load_package_list()
        self.collections = self.load_collections()

    def load_modules(self) -> Modules:
        """Loads all required packages."""
        spack = shutil.which("spack")
        if spack:
            spack_root = Path(spack).resolve().parent.parent
        else:
            spack_root = Path.cwd() / "spack"

        lib_path = spack_root / "lib/spack"

        for path in [lib_path, lib_path / "external"]:
            if path not in sys.path:
                sys.path.append(str(path))

        return self.Modules(
            config=importlib.import_module('spack.config'),
            repo=importlib.import_module('spack.repo'),
        )

    def load_repo_list(self) -> list:
        """Load a list of all repos."""
        return list(
            map(self.modules.repo.Repo, self.modules.config.get("repos"))
        )

    @dataclass
    class PackageBase:
        """Wrapper for a spack package."""

        name: str

    @dataclass
    class Package(PackageBase):
        """Wrapper for a spack package."""

        versions: list[str]

    def load_package_list(self) -> list[Package]:
        """Load a list of all packages."""
        return list(
            map(
                lambda package: self.Package(
                    name=package.name,
                    versions=[
                        str(ver) for ver in list(package.versions.keys())
                    ],
                ),
                itertools.chain.from_iterable(
                    list(
                        map(
                            lambda repo: repo.all_package_classes(), self.repos
                        )
                    )
                ),
            )
        )

    def filter_packages(self, prefix: str) -> list[Package]:
        """Filter packages based on a prefix."""
        regex = re.compile(fr"^{prefix}.*$")
        return list(filter(lambda p: regex.match(p.name), self.packages))

    @dataclass
    class Collection:
        """Spack package collection."""

        id: UUID
        name: str
        packages: list["Spack.Package"]

    def load_collections(self) -> list[Collection]:
        """Load package collections from Spack repo.

        Returns:
            list[Collection]: A list of package collections.
        """
        collections = {"Python": "py-", "R": "r-"}
        return [
            self.Collection(
                id=uuid.uuid4(),
                name=name,
                packages=self.filter_packages(prefix),
            )
            for name, prefix in collections.items()
        ]
