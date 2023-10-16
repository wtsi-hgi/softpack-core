"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import json
import subprocess
import tempfile
import threading
from dataclasses import dataclass


@dataclass
class PackageBase:
    """Wrapper for a spack package."""

    name: str


@dataclass
class Package(PackageBase):
    """Wrapper for a spack package."""

    versions: list[str]


class Spack:
    """Spack interface class."""

    def __init__(
        self, spack_exe: str = "spack", custom_repo: str = ""
    ) -> None:
        """Constructor."""
        self.stored_packages: list[Package] = []
        self.checkout_path = ""
        self.spack_exe = spack_exe
        self.custom_repo = custom_repo

    def load_package_list(self, spack_exe: str, custom_repo: str) -> None:
        """Load a list of all packages."""
        checkout_path = ""

        if custom_repo != "":
            tmp_dir = tempfile.TemporaryDirectory()
            checkout_path = tmp_dir.name
            self.checkout_custom_repo(custom_repo, checkout_path)

        self.store_packages_from_spack(spack_exe, checkout_path)

    def checkout_custom_repo(
        self, custom_repo: str, checkout_path: str
    ) -> None:
        """Clones the custom spack package repo to a local path.

        Args:
            custom_repo (str): URL to custom spack package repo.
            checkout_path (str): Path to clone custom spack repo to.
        """
        result = subprocess.run(
            ["git", "clone", "--depth", "1", custom_repo, checkout_path],
            capture_output=True,
        )

        result.check_returncode()

    def store_packages_from_spack(
        self, spack_exe: str, checkout_path: str
    ) -> None:
        """Reads the full list of available packages in spack and stores them.

        Args:
            spack_exe (str): Path to the spack executable.
            checkout_path (str): Path to the cloned custom spack repo.
        """
        if checkout_path == "":
            result = subprocess.run(
                [spack_exe, "list", "--format", "version_json"],
                capture_output=True,
            )
        else:
            result = subprocess.run(
                [
                    spack_exe,
                    "--config",
                    "repos:[" + checkout_path + "]",
                    "list",
                    "--format",
                    "version_json",
                ],
                capture_output=True,
            )

        pkgs = json.loads(result.stdout)

        self.stored_packages = list(
            map(
                lambda package: Package(
                    name=package.get("name"),
                    versions=[
                        str(ver) for ver in list(package.get("versions"))
                    ],
                ),
                pkgs,
            )
        )

    def packages(self) -> list[Package]:
        """Returns the list of stored packages.

        First generates the list if it is None.

        Returns:
            list[Package]: The stored list of spack packages.
        """
        if len(self.stored_packages) == 0:
            self.load_package_list(self.spack_exe, self.custom_repo)

        return self.stored_packages

    def keep_packages_updated(self, interval: float) -> None:
        """Runs package list retireval on a timer."""
        self.load_package_list(self.spack_exe, self.custom_repo)

        self.timer = threading.Timer(
            interval, self.keep_packages_updated, [interval]
        )
        self.timer.start()

    def stop_package_timer(self) -> None:
        """Stops any running timer threads."""
        if self.timer is not None:
            self.timer.cancel()
