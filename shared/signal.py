from pydantic import BaseModel, Field
from typing import Any

class Signal(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    reliability: float = Field(..., ge=0.0, le=1.0)
    module: str
    metadata: dict[str, Any] = {}