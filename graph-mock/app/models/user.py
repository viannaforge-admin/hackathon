from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class UserModel(BaseModel):
    id: str
    displayName: str
    userPrincipalName: str
    mail: str
    userType: Literal["Member", "Guest"]
    department: str
    jobTitle: str
