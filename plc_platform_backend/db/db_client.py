from __future__ import annotations

from functools import lru_cache

import motor
import motor.motor_asyncio

from plc_platform_backend.commons.configuration import get_configuration

DATABASE_NAME = "plc-testbench"


@lru_cache
def get_mongodb() -> MongoDB:
    return MongoDB()


class MongoDB:

    def __init__(self):
        self._client: motor.motor_asyncio.AsyncIOMotorClient = (
            motor.motor_asyncio.AsyncIOMotorClient(self._get_connection_string())
        )
        self._database: motor.motor_asyncio.AsyncIOMotorDatabase = (
            self.client.get_database(DATABASE_NAME)
        )

    @property
    def client(self) -> motor.motor_asyncio.AsyncIOMotorClient:
        return self._client

    @property
    def database(self) -> motor.motor_asyncio.AsyncIOMotorDatabase:
        return self._database

    def _get_connection_string(self) -> str:
        config = get_configuration()
        username = config.mongo_initdb_root_username
        password = config.mongo_initdb_root_password
        host = "mongo:27017"
        return f"mongodb://{username}:{password}@{host}"
