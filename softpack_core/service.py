"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import smtplib
import urllib.parse
from email.mime.text import MIMEText
from pathlib import Path

import typer
import uvicorn
import yaml
from fastapi import APIRouter, Request, Response, UploadFile
from typer import Typer
from typing_extensions import Annotated

from softpack_core.artifacts import Artifacts, State, artifacts
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

    @staticmethod
    @router.post("/requestRecipe")
    async def request_recipe(  # type: ignore[no-untyped-def]
        request: Request,
    ):
        """Request a recipe to be created."""
        data = await request.json()

        for key in ("name", "version", "description", "url", "username"):
            if key not in data or not isinstance(data[key], str):
                return {"error": "Invalid Input"}

        try:
            artifacts.create_recipe_request(
                Artifacts.RecipeObject(
                    data["name"],
                    data["version"],
                    data["description"],
                    data["url"],
                    data["username"],
                )
            )
        except Exception as e:
            return {"error": str(e)}

        recipeConfig = app.settings.recipes.dict()

        if all(
            key in recipeConfig and isinstance(recipeConfig[key], str)
            for key in ["fromAddr", "toAddr", "smtp"]
        ):
            msg = MIMEText(
                f'User: {data["username"]}\n'
                + f'Recipe: {data["name"]}\n'
                + f'Version: {data["version"]}\n'
                + f'URL: {data["url"]}\n'
                + f'Description: {data["description"]}'
            )
            msg["Subject"] = "SoftPack Recipe Request"
            msg["From"] = recipeConfig["fromAddr"]
            msg["To"] = recipeConfig["toAddr"]

            s = smtplib.SMTP(recipeConfig["smtp"])
            s.sendmail(
                recipeConfig["fromAddr"],
                [recipeConfig["toAddr"]],
                msg.as_string(),
            )
            s.quit()

        return {"message": "Request Created"}

    @staticmethod
    @router.get("/requestedRecipes")
    async def requested_recipes(  # type: ignore[no-untyped-def]
        request: Request,
    ):
        """List requested recipes."""
        return list(artifacts.iter_recipe_requests())

    @staticmethod
    @router.post("/fulfilRequestedRecipe")
    async def fulfil_recipe(  # type: ignore[no-untyped-def]
        request: Request,
    ):
        """Fulfil a recipe request."""
        data = await request.json()

        for key in ("name", "version", "requestedName", "requestedVersion"):
            if not isinstance(data[key], str):
                return {"error": "Invalid Input"}

        r = artifacts.get_recipe_request(
            data["requestedName"], data["requestedVersion"]
        )

        if r is None:
            return {"error": "Unknown Recipe"}

        for env in Environment.iter():
            if env.state != State.waiting:
                continue

            changed = False

            for pkg in env.packages:
                if (
                    pkg.name.startswith("*")
                    and pkg.name[1:] == data["requestedName"]
                    and pkg.version == data["requestedVersion"]
                ):
                    pkg.name = data["name"]
                    pkg.version = data["version"]
                    changed = True

                    break

            if not changed:
                continue

            artifacts.commit_and_push(
                artifacts.create_file(
                    Path(Artifacts.environments_root, env.path, env.name),
                    Artifacts.environments_file,
                    yaml.dump(
                        dict(
                            description=env.description,
                            packages=[
                                pkg.name
                                + ("@" + pkg.version if pkg.version else "")
                                for pkg in env.packages
                            ],
                        )
                    ),
                    False,
                    True,
                ),
                "fulfil recipe request for environment",
            )

            if not env.has_requested_recipes():
                Environment.submit_env_to_builder(
                    EnvironmentInput(
                        name=env.name,
                        path=env.path,
                        description=env.description,
                        packages=[
                            PackageInput(**vars(p)) for p in env.packages
                        ],
                    )
                )

        artifacts.remove_recipe_request(
            data["requestedName"], data["requestedVersion"]
        )

        return {"message": "Recipe Fulfilled"}

    @staticmethod
    @router.post("/removeRequestedRecipe")
    async def remove_recipe(  # type: ignore[no-untyped-def]
        request: Request,
    ):
        """Remove a recipe request."""
        data = await request.json()

        for key in ("name", "version"):
            if not isinstance(data[key], str):
                return {"error": "Invalid Input"}

        for env in Environment.iter():
            for pkg in env.packages:
                if (
                    pkg.name.startswith("*")
                    and pkg.name[1:] == data["name"]
                    and pkg.version == data["version"]
                ):
                    return {
                        "error": "There are environments relying on this "
                        + "requested recipe; can not delete."
                    }

        try:
            artifacts.remove_recipe_request(data["name"], data["version"])
        except Exception as e:
            return {"error": e}

        return {"message": "Request Removed"}
