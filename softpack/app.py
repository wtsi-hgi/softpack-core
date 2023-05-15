from typing import Any

import strawberry
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from singleton_decorator import singleton
from strawberry.fastapi import GraphQLRouter

from .config import Settings
from .query import Query


@singleton
class Application:
    """Application class."""

    def __init__(self) -> None:
        """Constructor."""
        self.settings = Settings.parse_obj({})
        self.schema = strawberry.Schema(query=Query)
        self.graphql_app = GraphQLRouter(self.schema)
        self.router = FastAPI()
        self.router.include_router(self.graphql_app, prefix="/graphql")
        self.router.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.server.header.origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


app = Application()


@app.router.get("/")
def root() -> Any:
    return {"message": "Softpack"}


schema = app.schema
