import uvicorn
from fastapi import FastAPI
from gql import Schema
from strawberry.fastapi import GraphQLRouter

from dynafield.base_model import CustomJSONResponse

app = FastAPI(default_response_class=CustomJSONResponse)
app.include_router(GraphQLRouter(Schema, graphql_ide="apollo-sandbox"), prefix="/graphql")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1000)
