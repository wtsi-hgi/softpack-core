"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from datetime import datetime

from .artifacts import Artifacts
from .schemas.environment import Environment


class Environments:
    """Environments."""

    def get(self) -> list[Environment]:
        """Get all environments.

        Returns:
            a list of environment objects
        """
        artifacts = Artifacts().get_artifacts()

        return [
            Environment(
                name=artifact.name,
                description=artifact.description,
                packages=artifact.packages,
                owner=artifact.owner,
                creation_date=datetime.now(),
                status="Completed",
                id=i,
            )
            for i, artifact in enumerate(artifacts)
        ]
