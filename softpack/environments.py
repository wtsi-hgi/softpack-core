from datetime import datetime

from .artifacts import Artifacts
from .schemas.strawberry.environment import Environment


class Environments:

    def get(self) -> list[Environment]:
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
