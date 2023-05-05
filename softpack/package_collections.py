from .schemas.strawberry.package import Package
from .schemas.strawberry.package_collection import PackageCollection


class PackageCollections:
    def get(self) -> list[PackageCollection]:
        collections = [
            PackageCollection(
                name="Python",
                packages=[
                    Package(name="numpy", version="1.24.2"),
                    Package(name="pandas", version="2.0.0"),
                    Package(name="matplotlib", version="3.7.1"),
                    Package(name="seaborn", version="0.12.2"),
                ],
                id=0,
            ),
            PackageCollection(
                name="R",
                packages=[
                    Package(name="tidyverse", version="2.0.0"),
                    Package(name="devtools", version="2.4.5"),
                ],
                id=1,
            ),
            PackageCollection(
                name="System",
                packages=[
                    Package(name="ant", version="1.10.3"),
                    Package(name="cmake", version="3.26.3"),
                ],
                id=2,
            ),
        ]

        return collections
