"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import strawberry

from .environments import Environments
from .package_collections import PackageCollections
from .schemas.strawberry.environment import Environment
from .schemas.strawberry.package_collection import PackageCollection
from .schemas.strawberry.user import User
from .users import Users


def all_environments() -> list[Environment]:
    """Get all environments.

    Returns:
        a list of environment objects
    """
    envs = Environments()
    return envs.get()


def all_package_collections() -> list[PackageCollection]:
    """Get all package collections.

    Returns:
        a list of package collection objects
    """
    collections = PackageCollections()
    return collections.get()


def all_users() -> list[User]:
    """Get all users.

    Returns:
        a user objects
    """
    users = Users()
    return users.get()


def find_environment(name: str) -> Environment:
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


def find_package_collection(name: str) -> PackageCollection:
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


def find_users(name: str) -> User:
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

    all_environments = strawberry.field(resolver=all_environments)
    all_packages = strawberry.field(resolver=all_package_collections)
    all_users = strawberry.field(resolver=all_users)
    find_environment = strawberry.field(resolver=find_environment)
    find_package_collection = strawberry.field(
        resolver=find_package_collection
    )
    find_users = strawberry.field(resolver=find_users)
