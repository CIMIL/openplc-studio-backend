from functools import lru_cache
from pydantic_settings import BaseSettings


@lru_cache
def get_configuration():
    return Configuration()

class Configuration(BaseSettings):
    mongo_initdb_root_username: str
    mongo_initdb_root_password: str