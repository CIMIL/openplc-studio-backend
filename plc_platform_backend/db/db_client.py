from __future__ import annotations

from functools import lru_cache

import motor
import motor.motor_asyncio

from plc_platform_backend.commons.configuration import get_configuration

@lru_cache
def get_mongodb() -> MongoDB:
    return MongoDB()


class MongoDB:

    def __init__(self):
        config = get_configuration()
        self._client: motor.motor_asyncio.AsyncIOMotorClient = (
            motor.motor_asyncio.AsyncIOMotorClient(
                host=config.mongo_host,
                port=config.mongo_port,
                username=config.mongo_initdb_root_username,
                password=config.mongo_initdb_root_password,
                authSource="admin",
            )
        )
        self._database: motor.motor_asyncio.AsyncIOMotorDatabase = (
            self.client.get_database(config.mongo_database)
        )

    @property
    def client(self) -> motor.motor_asyncio.AsyncIOMotorClient:
        return self._client

    @property
    def database(self) -> motor.motor_asyncio.AsyncIOMotorDatabase:
        return self._database
