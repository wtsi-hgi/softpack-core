import dataclasses
import itertools
from typing import Any, Callable, Iterable, TypeVar, Union

import strawberry
from strawberry.fastapi import GraphQLRouter

from .api import API
from .schemas.base import BaseSchema
from .schemas.environment import EnvironmentSchema
from .schemas.package_collection import PackageCollectionSchema

T = TypeVar('T')


class GraphQL(API):
    prefix = "/graphql"
    schemas = [EnvironmentSchema, PackageCollectionSchema]

    class Schema(strawberry.Schema):
        def __init__(self, schemas: list[type[object]]) -> None:
            self.schemas = schemas
            super().__init__(
                query=self.strawberry_class(BaseSchema.Query),
                mutation=self.strawberry_class(BaseSchema.Mutation),
            )

        def strawberry_class(self, obj: type) -> Union[T, Callable[[T], T]]:
            return strawberry.type(
                dataclasses.make_dataclass(
                    "_".join([self.__class__.__name__, obj.__name__]),
                    map(self.strawberry_field, self.get_fields(obj)),
                )
            )

        def get_fields(self, obj: type) -> Iterable:
            def fields(schema: type) -> tuple[Any, ...]:
                # def fields(schema: type) -> tuple[dataclasses.Field, ...]:
                try:
                    return dataclasses.fields(getattr(schema, obj.__name__))
                except AttributeError:
                    return ()

            return itertools.chain.from_iterable(map(fields, self.schemas))

        def strawberry_field(self, field: dataclasses.Field) -> Any:
            spec = [field.name, field.type]
            if field.default != dataclasses.MISSING:
                spec += [
                    dataclasses.field(
                        default=strawberry.field(resolver=field.default)
                    )
                ]
            return spec

    class Router(GraphQLRouter):
        def __init__(self, schema: strawberry.Schema, prefix: str) -> None:
            super().__init__(schema=schema, path=prefix)

    router = Router(schema=Schema(schemas), prefix=prefix)
