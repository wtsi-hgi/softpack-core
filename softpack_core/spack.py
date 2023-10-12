"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import importlib
import itertools
import json
import os
import re
import shutil
import sys
import subprocess
import tempfile
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

    def __init__(self, spack_exe: str = "spack", custom_repo: str = "") -> None:
        """Constructor."""
        # self.modules = self.load_modules()
        #self.repos = self.load_repo_list()
        self.stored_packages = None
        self.checkout_path = ""
        self.spack_exe = spack_exe
        self.custom_repo = custom_repo

    # def load_modules(self) -> Modules:
    #     """Loads all required packages."""
    #     spack = shutil.which("spack")
    #     if spack:
    #         spack_root = Path(spack).resolve().parent.parent
    #     else:
    #         spack_root = Path.cwd() / "spack"

    #     lib_path = spack_root / "lib/spack"

    #     for path in [lib_path, lib_path / "external"]:
    #         if path not in sys.path:
    #             sys.path.append(str(path))

    #     return self.Modules(
    #         config=importlib.import_module('spack.config'),
    #         repo=importlib.import_module('spack.repo'),
    #     )

    # def load_repo_list(self) -> list:
    #     """Load a list of all repos."""
    #     return list(
    #         map(self.modules.repo.Repo, self.modules.config.get("repos"))
    #     )

    @dataclass
    class PackageBase:
        """Wrapper for a spack package."""

        name: str

    @dataclass
    class Package(PackageBase):
        """Wrapper for a spack package."""

        versions: list[str]

    def load_package_list(self, spack_exe: str, custom_repo: str) -> list[Package]:
        """Load a list of all packages."""
        checkout_path = ""

        if custom_repo != "":
            tmp_dir = tempfile.TemporaryDirectory()
            checkout_path = tmp_dir.name
            self.checkout_custom_repo(custom_repo, checkout_path)

        return self.store_packages_from_spack(spack_exe, checkout_path)

        # return list(
        #     map(
        #         lambda package: self.Package(
        #             name=package.name,
        #             versions=[
        #                 str(ver) for ver in list(package.versions.keys())
        #             ],
        #         ),
        #         itertools.chain.from_iterable(
        #             list(
        #                 map(
        #                     lambda repo: repo.all_package_classes(), self.repos
        #                 )
        #             )
        #         ),
        #     )
        # )
    
    def checkout_custom_repo(self, custom_repo: str, checkout_path: str) -> None:
        result = subprocess.run(["git", "clone", "--depth", "1", custom_repo,
                                 checkout_path], capture_output=True)

        result.check_returncode()
    
    def store_packages_from_spack(
            self, spack_exe: str, checkout_path: str
        ) -> None:
        if checkout_path == "":
            result = subprocess.run([spack_exe,
                                 "list", "--format", "version_json"], capture_output=True)
        else:
            result = subprocess.run([spack_exe, "--config", "repos:["+checkout_path+"]",
                                 "list", "--format", "version_json"], capture_output=True)

        pkgs = json.loads(result.stdout)

        
        self.stored_packages = list(
            map(
               lambda package: self.Package(
                    name=package.get("name"),
                    versions=[
                        str(ver) for ver in list(package.get("versions"))
                    ],
                ),
                pkgs
            )
        )
    
    def packages(self) -> list[Package]:
        if self.stored_packages is None:
            self.load_package_list(self.spack_exe, self.custom_repo)
        
        return self.stored_packages
