"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from typing import Any

from .app import app
from .service import ServiceAPI

ServiceAPI.register()


def main(package_update_interval: float = 600) -> Any:
    """Main entrypoint."""
    return app.main(package_update_interval)


if __name__ == "__main__":
    main()
