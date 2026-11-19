from datetime import datetime

from pydantic import BaseModel


class ImageJobOut(BaseModel):
    id: str
    status: str
    garment: str
    input_url: str
    output_url: str | None
    error: str | None = None
    created_at: datetime
