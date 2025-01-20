from fastapi import FastAPI

from .routers import modules

app = FastAPI()


app.include_router(modules.router)
