from typing import Optional, List

from pydantic import BaseModel, Field


class FileReadRequest(BaseModel):
    path: str


class FileWriteRequest(BaseModel):
    path: str
    content: str


class ToolRequest(BaseModel):
    tool: str
    code: str
    gemini_key: Optional[str] = None
    deepseek_key: Optional[str] = None


class VSCodeRequest(BaseModel):
    path: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    model: Optional[str] = "gemini"
    gemini_key: Optional[str] = None
    deepseek_key: Optional[str] = None
    repo_url: Optional[str] = None
    github_token: Optional[str] = None


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    model: str


class CompletionRequest(BaseModel):
    code: str
    language: str = "python"
    position: int = 0
    gemini_key: Optional[str] = None
    deepseek_key: Optional[str] = None


class CompletionResponse(BaseModel):
    completion: str


class CloneRequest(BaseModel):
    repo_url: str
    target_dir: Optional[str] = None


class CloneResponse(BaseModel):
    status: str
    path: str


class FileReadResponse(BaseModel):
    content: str


class FileWriteResponse(BaseModel):
    status: str
    path: str


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    error: ErrorInfo
    requestId: Optional[str] = None
