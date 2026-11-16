from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class Task(BaseModel):
    task_type: str = "website_crawl"
    url: str
    output_format: str = "summary_and_json"
    max_pages: int = Field(default=5, ge=1, le=5)
    max_depth: int = Field(default=1, ge=0, le=1)
