from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    collection_name: str = Field(
        ...,
        min_length=1,
        description="Qdrant collection UUID from ingestion logs",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class AskResponse(BaseModel):
    answer: str = Field(..., description="LLM answer")
    sources: list[str] = Field(
        default_factory=list,
        description="Retrieved chunk texts used as context",
    )
