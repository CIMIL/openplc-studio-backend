import motor
import motor.motor_asyncio

from plc_platform_backend.db.db_client import MongoDB, get_mongodb


class BaseMongoDBRepository:
    def __init__(self, collection_name: str):
        mongodb: MongoDB = get_mongodb()
        self.collection: motor.motor_asyncio.AsyncIOMotorCollection = (
            mongodb.database.get_collection(collection_name)
        )
