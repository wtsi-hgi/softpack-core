"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import strawberry

from .environments import Environments
from .package_collections import PackageCollections
from .schemas.environment import Environment
from .schemas.package_collection import PackageCollection
from .schemas.user import User
from .users import Users


def environments() -> list[Environment]:
    """Get all environments.

    Returns:
        a list of environment objects
    """
    envs = Environments()
    return envs.get()


def environment(name: str) -> Environment:
    """Get environment by name.

    Args:
        name: the name of the environment

    Returns
        an environment object
    """
    envs = Environments().get()
    matching_envs = [env for env in envs if env.name == name]
    if len(matching_envs) > 0:
        return matching_envs[0]
    else:
        return None


def package_collections() -> list[PackageCollection]:
    """Get all package collections.

    Returns:
        a list of package collection objects
    """
    collections = PackageCollections()
    return collections.get()


def package_collection(name: str) -> PackageCollection:
    """Get package collection by name.

    Args:
        name: the name of the package collection

    Returns
        a package collection object
    """
    collections = PackageCollections().get()
    matching_collections = [
        collection for collection in collections if collection.name == name
    ]
    if len(matching_collections) > 0:
        return matching_collections[0]
    else:
        return None


def users() -> list[User]:
    """Get all users.

    Returns:
        a user objects
    """
    users = Users()
    return users.get()


def user(name: str) -> User:
    """Get user by name.

    Args:
        name: the name of the user

    Returns
        a user object
    """
    users = Users().get()
    matching_users = [user for user in users if user.name == name]
    if len(matching_users) > 0:
        return matching_users[0]
    else:
        return None


@strawberry.type
class Query:
    """GraphQL queries."""

    environments = strawberry.field(resolver=environments)
    environment = strawberry.field(resolver=environment)
    packages = strawberry.field(resolver=package_collections)
    package_collection = strawberry.field(resolver=package_collection)
    users = strawberry.field(resolver=users)
    user = strawberry.field(resolver=user)
