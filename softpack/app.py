from typing import Any, List
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from singleton_decorator import singleton
from .schemas.strawberry.environment import Environment
from .environments import Environments



@singleton
class Application:
    """Application class."""

    def __init__(self) -> None:
        """Constructor"""
        self.schema = strawberry.Schema(query=Query)
        self.graphql_app = GraphQLRouter(self.schema)
        self.router = FastAPI()
        self.router.include_router(self.graphql_app, prefix="/graphql")



@strawberry.type
class Query:
    @strawberry.field
    def env_count() -> int:
        envs = Environments()
        return len(envs.get())
    
    @strawberry.field
    def all_envs() -> List[Environment]:
        envs = Environments()
        return envs.get()
    



app = Application()

@app.router.get("/")
def root() -> Any:
    return {"message": "Softpack"}

# @app.router.get("/graphql", response_model=None)
# def graphql() -> List[Environment]:
#     envs = Environments()
#     return envs.get()


schema = app.schema
