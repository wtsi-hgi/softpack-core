"""Copyright (c) 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import pytest
from fastapi.testclient import TestClient

from softpack_core.app import app
from softpack_core.config.models import EmailConfig
from softpack_core.schemas.environment import (
    CreateEnvironmentSuccess,
    Environment,
    EnvironmentInput,
    PackageInput,
)
from softpack_core.spack import Package
from tests.integration.utils import builder_called_correctly

pytestmark = pytest.mark.repo


def test_request_recipe(httpx_post, testable_env_input, send_email):
    app.settings.recipes = EmailConfig(
        fromAddr="{}@domain.com",
        toAddr="hgi@domain.com",
        smtp="nothing",
    )

    client = TestClient(app.router)
    resp = client.post(
        url="/requestRecipe",
        json={
            "name": "a_recipe",
            "version": "1.2",
            "description": "A description",
            "url": "http://example.com",
            "username": "me",
        },
    )

    assert resp.json() == {"message": "Request Created"}

    assert send_email.call_count == 1

    assert send_email.call_args[0][0] == app.settings.recipes
    assert "Recipe:" in send_email.call_args[0][1]
    assert (
        send_email.call_args[0][2] == "SoftPack Recipe Request: a_recipe@1.2"
    )
    assert send_email.call_args[0][3] == "me"

    resp = client.get(url="/requestedRecipes")

    assert resp.json() == [
        {
            "name": "a_recipe",
            "version": "1.2",
            "description": "A description",
            "url": "http://example.com",
            "username": "me",
        }
    ]

    resp = client.post(
        url="/requestRecipe",
        json={
            "name": "a_recipe",
            "version": "1.2",
            "description": "A description",
            "url": "http://example.com",
            "username": "me",
        },
    )

    assert resp.json() == {"error": "File already exists"}

    resp = client.post(
        url="/requestRecipe",
        json={
            "nome": "a_recipe",
            "version": "1.2",
            "description": "A description",
            "url": "http://example.com",
            "username": "me",
        },
    )

    assert resp.json() == {"error": "Invalid Input"}

    resp = client.post(
        url="/requestRecipe",
        json={
            "name": "b_recipe",
            "version": "1.4",
            "description": "Another description",
            "url": "http://example.com",
            "username": "me2",
        },
    )

    assert resp.json() == {"message": "Request Created"}

    resp = client.get(url="/requestedRecipes")

    assert resp.json() == [
        {
            "name": "a_recipe",
            "version": "1.2",
            "description": "A description",
            "url": "http://example.com",
            "username": "me",
        },
        {
            "name": "b_recipe",
            "version": "1.4",
            "description": "Another description",
            "url": "http://example.com",
            "username": "me2",
        },
    ]

    env = EnvironmentInput.from_path("users/me/my_env-1")
    env.packages = [
        PackageInput.from_name("pkg@1"),
        PackageInput.from_name("*a_recipe@1.2"),
    ]

    existingEnvs = len(Environment.iter())

    assert isinstance(Environment.create(env), CreateEnvironmentSuccess)

    envs = Environment.iter()

    assert len(envs) == existingEnvs + 1
    assert len(envs[1].packages) == 2
    assert envs[1].packages[0].name == "pkg"
    assert envs[1].packages[0].version == "1"
    assert envs[1].packages[1].name == "*a_recipe"
    assert envs[1].packages[1].version == "1.2"

    httpx_post.assert_not_called()

    app.spack.stored_packages.append(
        Package(name="finalRecipe", versions=["1.2.1"])
    )

    try:
        resp = client.post(
            url="/fulfilRequestedRecipe",
            json={
                "name": "finalRecipe",
                "version": "1.2.1",
                "requestedName": "a_recipe",
                "requestedVersion": "1.2",
            },
        )

        assert resp.json() == {"message": "Recipe Fulfilled"}

        httpx_post.assert_called_once()

        env.name = "my_env-1"
        env.packages[1] = PackageInput.from_name("finalRecipe@1.2.1")

        builder_called_correctly(httpx_post, env)

        envs = Environment.iter()

        assert len(envs) == existingEnvs + 1
        assert len(envs[1].packages) == 2
        assert envs[1].packages[0].name == "pkg"
        assert envs[1].packages[0].version == "1"
        assert envs[1].packages[1].name == "finalRecipe"
        assert envs[1].packages[1].version == "1.2.1"

        resp = client.get(url="/requestedRecipes")

        assert resp.json() == [
            {
                "name": "b_recipe",
                "version": "1.4",
                "description": "Another description",
                "url": "http://example.com",
                "username": "me2",
            }
        ]

        resp = client.post(
            url="/removeRequestedRecipe",
            json={"name": "b_recipe", "version": "1.4"},
        )

        assert resp.json() == {"message": "Request Removed"}

        resp = client.get(url="/requestedRecipes")

        assert resp.json() == []

        resp = client.post(
            url="/requestRecipe",
            json={
                "name": "c_recipe",
                "version": "0.9",
                "description": "Lorem ipsum.",
                "url": "http://example.com",
                "username": "me",
            },
        )

        env = EnvironmentInput.from_path("users/me/my_env-2")
        env.packages = [
            PackageInput.from_name("pkg@1"),
            PackageInput.from_name("*c_recipe@0.9"),
        ]

        assert isinstance(Environment.create(env), CreateEnvironmentSuccess)

        resp = client.post(
            url="/removeRequestedRecipe",
            json={"name": "c_recipe", "version": "0.9"},
        )

        assert resp.json() == {
            "error": "There are environments relying on this requested recipe;"
            + " can not delete."
        }

        resp = client.post(
            url="/fulfilRequestedRecipe",
            json={
                "name": "no_recipe",
                "version": "1",
                "requestedName": "c_recipe",
                "requestedVersion": "0.9",
            },
        )

        assert resp.json() == {"error": "Unknown Recipe"}

        resp = client.post(
            url="/fulfilRequestedRecipe",
            json={
                "name": "finalRecipe",
                "version": "1",
                "requestedName": "c_recipe",
                "requestedVersion": "0.9",
            },
        )

        assert resp.json() == {"error": "Unknown Recipe"}

        resp = client.post(
            url="/fulfilRequestedRecipe",
            json={
                "name": "finalRecipe",
                "version": "1.2.1",
                "requestedName": "c_recipe",
                "requestedVersion": "0.9",
            },
        )

        assert resp.json() == {"message": "Recipe Fulfilled"}
    finally:
        app.spack.stored_packages.pop()
