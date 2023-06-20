"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from typing import Any

from .app import app
from .graphql import GraphQL
from .service import ServiceAPI

GraphQL.register()
ServiceAPI.register()


def main() -> Any:
    """Main entrypoint."""
    return app.main()


if __name__ == "__main__":
    main()
