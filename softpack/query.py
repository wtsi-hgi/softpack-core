"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from datetime import datetime

import strawberry

from .environments import Environments
from .package_collections import PackageCollections
from .schemas.environment import Environment
from .schemas.package import Package, PackageInput
from .schemas.package_collection import PackageCollection
from .schemas.user import User, UserInput
from .users import Users


# Query resolvers
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
        a list of user objects
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


# Mutation resolvers
def add_environment(
    name: str,
    description: str,
    packages: list[PackageInput],
    owner: UserInput,
    creation_date: datetime,
    status: str,
    id: int,
) -> Environment:
    """Add a new environment.

    Args:
        name: the name of the environment
        description: a description of the environment
        packages: a list of packages contained in the environment
        owner: the owner of the environment
        creation_date: the datetime of when the environment was created
        status: the build status of the environment - Completed/Pending/Failed
        id: the id of the environment

    Returns:
        an Environment object
    """
    pkgs = [pkg.create_instance() for pkg in packages]
    owner = owner.create_instance()
    new_env = Environment(
        name=name,
        description=description,
        packages=pkgs,
        owner=owner,
        creation_date=creation_date,
        status=status,
        id=id,
    )
    return new_env


def add_package(name: str, version: str = None) -> Package:
    """Add a new package.

    Args:
        name: the name of the package
        version: the version of the package

    Returns:
        a Package object
    """
    return Package(name=name, version=version)


def add_package_collection(
    name: str, packages: list[PackageInput], id: int
) -> PackageCollection:
    """Add a new package collection.

    Args:
        name: the name of the package collection
        packages: the list of packages in the package collection
        id: the id of the package collection

    Returns:
        a PackageCollection object
    """
    pkgs = [pkg.create_instance() for pkg in packages]
    return PackageCollection(name=name, packages=pkgs, id=id)


def add_user(name: str, id: int) -> Package:
    """Add a new package.

    Args:
        name: the name of the package
        version: the version of the package

    Returns:
        a User object
    """
    return Package(name=name, id=id)


@strawberry.type
class Query:
    """GraphQL queries."""

    environments: list[Environment] = strawberry.field(resolver=environments)
    environment: Environment = strawberry.field(resolver=environment)
    packages: list[PackageCollection] = strawberry.field(
        resolver=package_collections
    )
    package_collection: PackageCollection = strawberry.field(
        resolver=package_collection
    )
    users: list[User] = strawberry.field(resolver=users)
    user: User = strawberry.field(resolver=user)


@strawberry.type
class Mutation:
    """GraphQL mutations."""

    add_environment: Environment = strawberry.mutation(
        resolver=add_environment
    )
    add_package: Package = strawberry.mutation(resolver=add_package)
    add_package_collection: PackageCollection = strawberry.mutation(
        resolver=add_package_collection
    )
    add_user: User = strawberry.mutation(resolver=add_user)
