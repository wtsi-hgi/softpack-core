"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import uvicorn

from softpack.app import app


def main():
    """Start the Softpack Core GraphQL API service.

    Returns:
        None
    """
    uvicorn.run(
        "softpack.app:app.router",
        host=app.settings.server.host,
        port=app.settings.server.port,
        reload=True,
        log_level="debug",
    )


if __name__ == "__main__":
    main()
