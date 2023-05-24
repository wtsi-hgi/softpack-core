"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import dataclasses
import itertools
from typing import Any, Callable, Iterable, Tuple, Union, cast

import strawberry
from strawberry.fastapi import GraphQLRouter
from typer import Typer
from typing_extensions import Type

from .api import API
from .app import app
from .schemas.base import BaseSchema
from .schemas.environment import EnvironmentSchema
from .schemas.package_collection import PackageCollectionSchema


class GraphQL(API):
    """GraphQL API."""

    prefix = "/graphql"
    schemas = [EnvironmentSchema, PackageCollectionSchema]
    commands = Typer(help="GraphQL commands.")

    @staticmethod
    @commands.command("query", help="Execute a GraphQL query.")
    def query_command() -> None:
        """Execute a GraphQL query.

        Returns:
            None.
        """
        app.echo("GraphQL Query")

    class Schema(strawberry.Schema):
        """GraphQL Schema class."""

        def __init__(self, schemas: list[type[object]]) -> None:
            """Constructor.

            Args:
                schemas: List of schema providers.
            """
            self.schemas = schemas
            super().__init__(
                query=self.strawberry_class(BaseSchema.Query),
                mutation=self.strawberry_class(BaseSchema.Mutation),
            )

        def strawberry_class(self, obj: Type[Any]) -> Type[Any]:
            """Define a new dataclass wrapped in a strawberry.type.

            Args:
                obj: The type used for defining a new strawberry class.

            Returns:
                Type[Any]: A new dataclass type.

            """
            return strawberry.type(
                dataclasses.make_dataclass(
                    "_".join([self.__class__.__name__, obj.__name__]),
                    map(self.strawberry_field, self.get_fields(obj)),
                )
            )

        def get_fields(self, obj: Type[Any]) -> Iterable:
            """Get fields of a dataclass.

            Args:
                obj: A dataclass object or instance.

            Returns:
                Iterable: An iterable over a list of dataclass fields.
            """

            def fields(schema: Type[Any]) -> tuple[Any, ...]:
                try:
                    return dataclasses.fields(getattr(schema, obj.__name__))
                except AttributeError:
                    return ()

            return itertools.chain.from_iterable(map(fields, self.schemas))

        def strawberry_field(
            self, field: dataclasses.Field
        ) -> Union[Tuple[str, type], Tuple[str, type, Any]]:
            """Get strawberry field.

             Get strawberry field as a tuple of dataclass name, type and
             dataclass.Field.

            Args:
                field: A dataclass field.

            Returns:
                tuple: dataclass name, type and dataclass.Field.
            """
            spec = (field.name, field.type)
            if field.default == dataclasses.MISSING:
                return spec

            return (
                *spec,
                dataclasses.field(
                    default=strawberry.field(
                        resolver=cast(Callable[..., Any], field.default)
                    )
                ),
            )

    class Router(GraphQLRouter):
        """GraphQL router."""

        def __init__(self, schema: strawberry.Schema, prefix: str) -> None:
            """Constructor.

            Args:
                schema: GraphQL schema
                prefix: Path prefix for the GraphQL route.
            """
            super().__init__(schema=schema, path=prefix)

    router = Router(schema=Schema(schemas), prefix=prefix)
