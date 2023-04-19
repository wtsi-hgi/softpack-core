from typing import List
from .schemas.strawberry.package import Package


class Packages:
    
    def get(self) -> List[Package]:
        pkgs = [
            Package(
                name="Python",
                version="3.10",
            ),
            Package(
                name="R",
                version="3.4.0",
            )
        ]
        return pkgs