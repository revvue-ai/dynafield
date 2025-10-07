import uvicorn
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from dynafield.base_model import CustomJSONResponse
from example.gql import Schema

app = FastAPI(default_response_class=CustomJSONResponse)
app.include_router(GraphQLRouter(Schema), prefix="/graphql")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1000)
