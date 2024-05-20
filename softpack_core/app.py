"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, NoReturn

import typer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from singleton_decorator import singleton
from typer import Typer

from softpack_core import __version__
from softpack_core.spack import Spack

from .config.settings import Settings
from .url import URL


@singleton
class Application:
    """Application class."""

    commands = Typer()
    router = FastAPI()

    @staticmethod
    @router.get("/")
    def status() -> dict[str, Any]:
        """HTTP GET handler for / route.

        Returns:
            dict: Application status to return.
        """
        return {
            "time": str(datetime.now()),
            "softpack": {"core": {"version": __version__}},
        }

    def __init__(self) -> None:
        """Constructor."""
        self.settings = Settings.parse_obj({})
        self.spack = Spack(
            self.settings.spack.bin,
            self.settings.spack.repo,
            self.settings.spack.cache,
        )

        self.router.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.server.header.origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def register_api(self, api: Any) -> None:
        """Register an API with the application.

        Args:
            api: An API class to register.

        Returns:
            None.
        """

        def include_router() -> None:
            return self.router.include_router(api.router)

        def add_typer() -> None:
            name = Path(api.prefix).name
            return self.commands.add_typer(api.commands, name=name)

        for registry_func in [include_router, add_typer]:
            try:
                registry_func()
            except AttributeError as e:
                typer.echo(e)

    def echo(self, *args: Any, **kwargs: Any) -> Any:
        """Print a message using Typer/Click echo.

        Args:
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Any: The return value from Typer.echo.
        """
        return typer.echo(*args, **kwargs)

    @staticmethod
    def url(path: str = "/", scheme: str = "http") -> str:
        """Get absolute URL path.

        Args:
            path: Relative URL path
            scheme: URL scheme

        Returns:
            str: URL path
        """
        url = URL(
            scheme=scheme,
            netloc=f"{app.settings.server.host}:{app.settings.server.port}",
            path=path,
        )
        return str(url)

    def main(self, package_update_interval: float) -> NoReturn:
        """Main command line entrypoint.

        Args:
            package_update_interval: interval between updates of the spack
        package list. Setting 0 disables the automatic updating.
        """
        if package_update_interval > 0:
            self.spack.keep_packages_updated(package_update_interval)

        self.commands()
        assert False  # self.commands() does not return


app = Application()
