from datetime import datetime
from typing import Annotated, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, Field

PyObjectId = Annotated[str, BeforeValidator(str)]


class BaseDocument(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default_factory=lambda: ObjectId())
    created: Optional[datetime] = Field(default_factory=lambda: datetime.utcnow())
    updated: Optional[datetime] = Field(default_factory=lambda: datetime.utcnow())
