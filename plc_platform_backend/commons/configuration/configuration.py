from functools import lru_cache

from pydantic_settings import BaseSettings


@lru_cache
def get_configuration():
    return Configuration()


class Configuration(BaseSettings):
    mongo_initdb_root_username: str
    mongo_initdb_root_password: str
    plc_root_folder: str
    plugins_folder: str
    redis_url: str

    def validate(self):
        for field_name in [
            "mongo_initdb_root_username",
            "mongo_initdb_root_password",
            "plc_root_folder",
            "plugins_folder",
            "redis_url",
        ]:
            value = getattr(self, field_name)
            if not value or (isinstance(value, str) and value.strip() == ""):
                raise ValueError(f"Configuration field '{field_name}' cannot be blank.")
