from pydantic import BaseModel, Field
from typing import List, Optional

class Alternative(BaseModel):
    letter: str = Field(pattern="^[A-E]$")
    text: str

class ImageDesc(BaseModel):
    src: str
    img_desc_raw: Optional[str] = None

class Question(BaseModel):
    number: int
    full_text: str
    alternatives: List[Alternative] = []
    images: List[ImageDesc] = []

class Exam(BaseModel):
    exam: str
    questions: List[Question]
