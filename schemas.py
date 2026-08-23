from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TaskCreate(BaseModel):
    title: str
    done: bool = False


class TaskOut(BaseModel):
    id: int
    title: str
    done: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
