from pydantic import BaseModel

from features.auditor.schemas import BaseResponse


class ManagerSchema(BaseModel):
    id: str
    name: str
    email: str
    role: str


class AuditorSchema(BaseModel):
    id: str
    name: str
    email: str
    role: str
    manager: str


class CheckAuthSchema(BaseResponse):
    user: AuditorSchema | ManagerSchema
