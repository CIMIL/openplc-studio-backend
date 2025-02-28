from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from plc_platform_backend.db import get_mongodb
from plc_platform_backend.routers import modules, runs


async def db_setup(app: FastAPI):
    # Startup
    mongodb = get_mongodb()
    ping_response = await mongodb.database.command("ping")

    if int(ping_response["ok"]) != 1:
        raise Exception("Problem connecting to database cluster.")
    else:
        print("Connected to database cluster.")

    yield

    # Shutdown
    mongodb = get_mongodb()
    mongodb.client.close()


app = FastAPI(lifespan=db_setup)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(modules.router)
app.include_router(runs.router)
