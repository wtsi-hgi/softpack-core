from itertools import zip_longest
from pathlib import Path
from typing import Optional

import yaml
from box import Box

from softpack.schemas.strawberry.environment import Environment
from softpack.schemas.strawberry.package import Package
from softpack.schemas.strawberry.user import User


class Artifacts:
    @staticmethod
    def package_components(package: str) -> Box[dict[str, Optional[str]]]:
        """Returns the name and version of the package."""

        keys = ["name", "version"]
        return Box(dict(zip_longest(keys, package.split("@"), fillvalue=None)))

    def get_artifacts(self) -> list[Environment]:
        """Get the list of artifacts."""

        repo_path = Path().cwd().parent.parent / "softpack-artifacts"
        artifacts = []
        for pth in Path(repo_path / "environments" / "users").rglob(
            "softpack.yml"
        ):
            with open(pth) as file:
                env = Box(yaml.safe_load(file))
                env.name = pth.parent.name
                env.owner = User(name=pth.parent.parent.name, id=0)
                env.packages = [
                    Package(
                        name=self.package_components(package).name,
                        version=self.package_components(package).version,
                    )
                    for package in env.packages
                ]
                artifacts.append(env)

        return artifacts
