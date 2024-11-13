"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


import smtplib
import statistics
import urllib.parse
from email.mime.text import MIMEText
from pathlib import Path
from typing import Tuple, Union, cast

import typer
import uvicorn
import yaml
from fastapi import APIRouter, Request, Response, UploadFile
from typer import Typer
from typing_extensions import Annotated

from softpack_core.artifacts import Artifacts, State, artifacts
from softpack_core.config.models import EmailConfig
from softpack_core.schemas.environment import (
    AddTagInput,
    BuilderError,
    BuildStatus,
    CreateEnvironmentSuccess,
    DelEnvironmentInput,
    Environment,
    EnvironmentInput,
    PackageInput,
    SetHiddenInput,
    WriteArtifactSuccess,
)
from softpack_core.schemas.groups import Group
from softpack_core.schemas.package_collection import PackageCollection

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

        Environment.init(branch)

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

        path = Path(env_path)
        env = Environment.get_env(path.parent, path.name)
        newState = State.queued
        files = cast(list[Union[UploadFile, Tuple[str, str]]], file)

        if env:
            for i in range(len(file)):
                f = file[i]
                if f.filename == artifacts.builder_out:
                    newState = State.failed

                    contents = cast(str, (await f.read()).decode())

                    if (
                        "concretization failed for the following reasons:"
                        in contents
                    ):
                        await env.update_metadata(
                            "failure_reason", "concretization"
                        )
                        env.failure_reason = "concretization"
                    else:
                        await env.update_metadata("failure_reason", "build")
                        env.failure_reason = "build"

                    files[i] = (f.filename, contents)

                if f.filename == artifacts.module_file:
                    newState = State.ready

                    break

            if (
                newState != State.queued
                and env.username is not None
                and env.username != ""
            ):
                envEmailConfig = app.settings.environments
                m = (
                    "built sucessfully"
                    if newState == State.ready
                    else "failed to build"
                )

                e = (
                    ""
                    if newState == State.ready
                    else "\nThe error was a build error. "
                    + "Contact your softpack administrator.\n"
                    if env.failure_reason == "build"
                    else "\nThe error was a version conflict. "
                    + "Try relaxing which versions you've specified.\n"
                )

                message = (
                    f"Hi {env.username},\n"
                    + "\n"
                    + f"Your environment, {env_path}, has {m}.\n"
                    + e
                    + "\n"
                    + "SoftPack Team"
                )

                subject = (
                    "Your environment is ready!"
                    if newState == State.ready
                    else "Your environment failed to build"
                )

                send_email(
                    envEmailConfig,
                    message,
                    subject,
                    env.username,
                    newState != State.ready,
                )
                await env.remove_username()

        resp = await Environment.write_artifacts(env_path, files)
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
    @router.post("/request-recipe")
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

        if data["username"] != "":
            recipeConfig = app.settings.recipes

            send_email(
                recipeConfig,
                f'User: {data["username"]}\n'
                + f'Recipe: {data["name"]}\n'
                + f'Version: {data["version"]}\n'
                + f'URL: {data["url"]}\n'
                + f'Description: {data["description"]}',
                f'SoftPack Recipe Request: {data["name"]}@{data["version"]}',
                data["username"],
            )

        return {"message": "Request Created"}

    @staticmethod
    @router.get("/requested-recipes")
    async def requested_recipes(  # type: ignore[no-untyped-def]
        request: Request,
    ):
        """List requested recipes."""
        return list(artifacts.iter_recipe_requests())

    @staticmethod
    @router.post("/fulfil-requested-recipe")
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

        if r is None or not any(
            version == data["version"]
            for pkg in app.spack.stored_packages
            if pkg.name == data["name"]
            for version in pkg.versions
        ):
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

            await Environment.write_artifacts(
                str(Path(env.path, env.name)),
                [
                    (
                        Artifacts.environments_file,
                        yaml.dump(
                            dict(
                                description=env.description,
                                packages=[
                                    pkg.name
                                    + (
                                        "@" + pkg.version
                                        if pkg.version
                                        else ""
                                    )
                                    for pkg in env.packages
                                ],
                            )
                        ),
                    )
                ],
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
    @router.post("/remove-requested-recipe")
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

    @staticmethod
    @router.post("/get-recipe-description")
    async def recipe_description(  # type: ignore[no-untyped-def]
        request: Request,
    ):
        """Return the description for a recipe."""
        data = await request.json()

        if (
            not isinstance(data["recipe"], str)
            or data["recipe"] not in app.spack.descriptions
        ):
            return {"error": "Invalid Input"}

        return {"description": app.spack.descriptions[data["recipe"]]}

    @staticmethod
    @router.post("/build-status")
    async def buildStatus(  # type: ignore[no-untyped-def]
        request: Request,
    ):
        """Return the avg wait seconds and a map of names to build status."""
        statuses = BuildStatus.get_all()
        if isinstance(statuses, BuilderError):
            statuses = []

        try:
            avg_wait_secs = statistics.mean(
                (s.build_done - s.requested).total_seconds()
                for s in statuses
                if s.build_done is not None
            )
        except statistics.StatisticsError:
            avg_wait_secs = None

        return {
            "avg": avg_wait_secs,
            "statuses": map(
                lambda x: (x.name, x.build_start),
                filter(lambda x: x.build_start is not None, statuses),
            ),
        }

    @staticmethod
    @router.post("/create-environment")
    def create_env(  # type: ignore[no-untyped-def]
        env: EnvironmentInput,
    ):
        """Endpoint for creating environments."""
        return Environment.create(env)

    @staticmethod
    @router.get("/get-environments")
    def get_envs():  # type: ignore[no-untyped-def]
        """Endpoint for creating environments."""
        return Environment.iter()

    @staticmethod
    @router.post("/delete-environment")
    def delete_env(  # type: ignore[no-untyped-def]
        env: DelEnvironmentInput,
    ):
        """Endpoint for deleting environments."""
        return Environment.delete(env.name, env.path)

    @staticmethod
    @router.post("/add-tag")
    async def add_tag_env(  # type: ignore[no-untyped-def]
        tag: AddTagInput,
    ):
        """Endpoint for adding a tag."""
        return await Environment.add_tag(tag.name, tag.path, tag.tag)

    @staticmethod
    @router.post("/set-hidden")
    async def set_hidden(  # type: ignore[no-untyped-def]
        hide: SetHiddenInput,
    ):
        """Endpoint for setting hidden."""
        return await Environment.set_hidden(hide.name, hide.path, hide.hidden)

    @staticmethod
    @router.post("/upload-module")
    async def upload_module(  # type: ignore[no-untyped-def]
        module_path: str,
        environment_path: str,
        file: Request,
    ):
        """Endpoint for uploading a module."""
        data = await file.body()

        return await Environment.create_from_module(
            data, module_path, environment_path
        )

    @staticmethod
    @router.post("/update-module")
    async def update_module(  # type: ignore[no-untyped-def]
        module_path: str,
        environment_path: str,
        file: Request,
    ):
        """Endpoint for updating a module."""
        data = await file.body()

        return await Environment.update_from_module(
            data, module_path, environment_path
        )

    @staticmethod
    @router.get("/package-collection")
    def package_collection():  # type: ignore[no-untyped-def]
        """Endpoint for returning spack recipes."""
        return PackageCollection.iter()

    @staticmethod
    @router.post("/groups")
    async def groups(request: Request):  # type: ignore[no-untyped-def]
        """Endpoint for finding groups from a username."""
        username = await request.json()

        if not isinstance(username, str):
            return {"error": "invalid username"}

        return (group.name for group in Group.from_username(username))


def send_email(
    emailConfig: EmailConfig,
    message: str,
    subject: str,
    username: str,
    sendAdmin: bool = True,
) -> None:
    """The send_email functions sends an email."""
    if (
        emailConfig.fromAddr is None
        or emailConfig.toAddr is None
        or emailConfig.smtp is None
    ):
        return

    msg = MIMEText(message)

    fromAddr = emailConfig.fromAddr.format(username)
    toAddr = emailConfig.toAddr.format(username)

    msg["Subject"] = subject
    msg["From"] = fromAddr
    msg["To"] = toAddr

    localhostname = None

    if emailConfig.localHostname is not None:
        localhostname = emailConfig.localHostname

    s = smtplib.SMTP(emailConfig.smtp, local_hostname=localhostname)
    s.sendmail(
        fromAddr,
        [toAddr, emailConfig.adminAddr]
        if sendAdmin and emailConfig.adminAddr is not None
        else [toAddr],
        msg.as_string(),
    )
    s.quit()
