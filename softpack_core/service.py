"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import urllib.parse
from multiprocessing.synchronize import Event as EventClass
from pathlib import Path

import typer
import uvicorn
from fastapi import APIRouter, Request, Response, UploadFile
from typer import Typer
from typing_extensions import Annotated

from softpack_core.artifacts import State, artifacts
from softpack_core.schemas.environment import (
    CreateEnvironmentSuccess,
    Environment,
    EnvironmentInput,
    PackageInput,
    WriteArtifactSuccess,
)

from .api import API
from .app import app


class ServiceAPI(API):
    """Service module."""

    prefix = "/service"
    commands = Typer(help="Commands for managing core service.")
    router = APIRouter()

    @staticmethod
    @commands.command(help="Start the SoftPack Core API service.")
    def run(
        reload: Annotated[
            bool,
            typer.Option(
                "--reload",
                help="Automatically reload when changes are detected.",
            ),
        ] = False,
        branch: Annotated[
            str,
            typer.Option(
                "--branch",
                help="Create and use this branch of Artefacts repo.",
            ),
        ] = 'main',
    ) -> None:
        """Start the SoftPack Core REST API service.

        Args:
            reload: Enable auto-reload.
            branch: branch to use

        Returns:
            None.
        """
        if branch != 'main':
            print(f'Changing branch to {branch}')
            # FIXME do only when branch does not exist
            artifacts.create_remote_branch(branch)

        artifacts.clone_repo(branch=branch)

        uvicorn.run(
            "softpack_core.app:app.router",
            host=app.settings.server.host,
            port=app.settings.server.port,
            reload=reload,
            log_level="debug",
        )

    @staticmethod
    @router.post("/upload")
    async def upload_artifacts(  # type: ignore[no-untyped-def]
        request: Request,
        file: list[UploadFile],
    ):
        """upload_artifacts is a POST fn that adds files to an environment.

          The environment does not need to exist already.

        Args:
            file (List[UploadFile]): The files to be uploaded.
            request (Request): The POST request which contains the environment
            path in the query.

        Returns:
            WriteArtifactResponse
        """
        env_path = urllib.parse.unquote(request.url.query)
        if Environment.check_env_exists(Path(env_path)) is not None:
            create_response = Environment.create_new_env(
                EnvironmentInput.from_path(env_path),
                artifacts.built_by_softpack_file,
            )

            if not isinstance(create_response, CreateEnvironmentSuccess):
                return create_response

        resp = await Environment.write_artifacts(env_path, file)
        if not isinstance(resp, WriteArtifactSuccess):
            raise Exception(resp)

        return resp

    @staticmethod
    @router.post("/resend-pending-builds")
    async def resend_pending_builds(  # type: ignore[no-untyped-def]
        response: Response,
    ):
        """Resubmit any pending builds to the builder."""
        successes = 0
        failures = 0
        for env in Environment.iter():
            if env.state != State.queued:
                continue
            result = Environment.submit_env_to_builder(
                EnvironmentInput(
                    name=env.name,
                    path=env.path,
                    description=env.description,
                    packages=[PackageInput(**vars(p)) for p in env.packages],
                )
            )
            if result is None:
                successes += 1
            else:
                failures += 1

        if failures == 0:
            message = "Successfully triggered resends"
        else:
            response.status_code = 500
            message = "Failed to trigger all resends"

        return {
            "message": message,
            "successes": successes,
            "failures": failures,
        }
