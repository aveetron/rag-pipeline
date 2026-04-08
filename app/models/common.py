from pydantic import BaseModel, Field

class ApiResponse(BaseModel):
    message: str = Field(..., description="The message to return")
    success_code: int = Field(..., description="The success code to return")

    @classmethod
    def success(cls, message: str) -> "ApiResponse":
        return cls(message=message, success_code=200)

    @classmethod
    def error(cls, message: str) -> "ApiResponse":
        return cls(message=message, success_code=400)
