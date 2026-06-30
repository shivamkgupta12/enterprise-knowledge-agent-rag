from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class ChatFilters(BaseModel):
    department: str | None = None
    doc_type: str | None = None
    sensitivity: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3)
    conversation: list[Message] = []
    filters: ChatFilters = ChatFilters()
    debug: bool = False


class Citation(BaseModel):
    id: str
    title: str
    source_file: str
    source_url: str
    page: int
    content_preview: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    rewritten_query: str
    subqueries: list[str]
    latency_ms: int
    retrieval_debug: list[dict] | None = None


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None
    citations: list[str] = []
