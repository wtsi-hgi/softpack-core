from typing import Any
import strawberry
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
        origins = [
                "http://localhost",
                "http://localhost:8080",
                "http://localhost:3000",
            ]
        self.router.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )



app = Application()

@app.router.get("/")
def root() -> Any:
    return {"message": "Softpack"}


schema = app.schema
