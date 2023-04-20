from typing import Any
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from singleton_decorator import singleton
from .query import Query



@singleton
class Application:
    """Application class."""

    def __init__(self) -> None:
        """Constructor"""
        self.schema = strawberry.Schema(query=Query)
        self.graphql_app = GraphQLRouter(self.schema)
        self.router = FastAPI()
        self.router.include_router(self.graphql_app, prefix="/graphql")




app = Application()

@app.router.get("/")
def root() -> Any:
    return {"message": "Softpack"}


schema = app.schema
