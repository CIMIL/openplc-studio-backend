from datetime import datetime
from typing import Annotated, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

PyObjectId = Annotated[str, BeforeValidator(str)]


class BaseDocument(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    created: Optional[datetime] = Field(default_factory=lambda: datetime.utcnow())
    updated: Optional[datetime] = Field(default_factory=lambda: datetime.utcnow())
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
