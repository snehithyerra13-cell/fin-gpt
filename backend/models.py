from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class User(BaseModel):
    email: str
    password: str


class Chat(BaseModel):
    user_email: str
    message: str
    response: str


class PDFResult(BaseModel):
    user_id: Optional[str] = None
    filename: str
    result: Dict
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QueryLog(BaseModel):
    user_id: Optional[str] = None
    query: str
    answer: str
    source: str
    created_at: datetime
