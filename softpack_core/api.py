"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path

from .app import app


class API:
    """API base class."""

    prefix = "/"

    @classmethod
    def register(cls) -> None:
        """Register the API with the application.

        Returns:
            None.
        """
        app.register_api(cls)

    @classmethod
    def command(cls, command: str, *args: str) -> list[str]:
        """Build a command with arguments.

        Args:
            command: Command to run
            *args: Positional arguments

        Returns:
            list[str]: A build command line to execute.

        """
        return [Path(cls.prefix).name, command, *args]

    @classmethod
    def url(cls, path: str) -> str:
        """Get absolute URL path.

        Args:
            path: Relative URL path under module prefix.

        Returns:
            str: URL path
        """
        return app.url(path=str(Path(cls.prefix) / path))
