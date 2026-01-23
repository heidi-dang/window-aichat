from typing import Optional, List, Dict
from pydantic import BaseModel

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

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []
    model: Optional[str] = "gemini"
    gemini_key: Optional[str] = None
    deepseek_key: Optional[str] = None
    repo_url: Optional[str] = None
    github_token: Optional[str] = None

class CompletionRequest(BaseModel):
    code: str
    language: str = "python"
    position: int = 0
    gemini_key: Optional[str] = None
    deepseek_key: Optional[str] = None

class CloneRequest(BaseModel):
    repo_url: str
    target_dir: Optional[str] = None
