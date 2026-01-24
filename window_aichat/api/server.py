import os
import sys
import logging
import json
import uuid
import asyncio
import threading
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, UploadFile, File, Depends, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field

# Import from internal packages
try:
    from window_aichat.core.ai_client import AIChatClient
    AI_CORE_AVAILABLE = True
except ImportError:
    AI_CORE_AVAILABLE = False
    print("Warning: ai_core module not found. AI features will be limited.")

from window_aichat.schemas.api_models import (
    FileReadRequest,
    FileWriteRequest,
    ToolRequest,
    VSCodeRequest,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CompletionRequest,
    CompletionResponse,
    CloneRequest,
    CloneResponse,
    FileReadResponse,
    FileWriteResponse,
)
from window_aichat.core.context import PromptTemplate
from window_aichat.core.tokens import Tokenizer
from window_aichat.db.session import get_db, engine
from window_aichat.db.models import Base, User, ProjectSession, SessionMessage, MemoryItem, EmbeddingItem, AuditLog
from window_aichat.db.auth import hash_password, verify_password, issue_token, decode_token
from window_aichat.db.limits import RateLimiter, RateLimitConfig
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("window_aichat.api.server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Window AI Chat Backend", lifespan=lifespan)

MAX_CONTEXT_TOKENS = int(os.getenv("WINDOW_AICHAT_MAX_CONTEXT_TOKENS", "8000"))
_prompt_template = PromptTemplate()
_tokenizer = Tokenizer()
_require_auth = os.getenv("WINDOW_AICHAT_REQUIRE_AUTH", "0") == "1"
_rate_limiter = RateLimiter(
    RateLimitConfig(
        window_seconds=int(os.getenv("WINDOW_AICHAT_RATE_LIMIT_WINDOW", "60")),
        max_requests=int(os.getenv("WINDOW_AICHAT_RATE_LIMIT_MAX", "240")),
    )
)

def build_prompt_from_history(history: List[Dict[str, str]], user_message: str) -> str:
    messages = _prompt_template.format_messages(history, user_message)
    trimmed = _tokenizer.trim_context(messages, MAX_CONTEXT_TOKENS)
    return "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in trimmed])


def _get_request_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _get_bearer_token(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization")
    if not header:
        return None
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = _get_bearer_token(request)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db.get(User, str(user_id))
    return user


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    key = f"ip:{_get_request_ip(request)}"
    allowed, remaining, reset_in = _rate_limiter.allow(key)
    if not allowed:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=429,
            content=_error_payload("rate_limited", "Too many requests", request_id, details={"resetInSeconds": reset_in}),
            headers={"X-RateLimit-Remaining": str(remaining), "X-RateLimit-Reset": str(reset_in)},
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_in)
    return response

def _error_payload(code: str, message: str, request_id: Optional[str], details: Optional[dict] = None) -> dict:
    payload: dict = {"error": {"code": code, "message": message}, "requestId": request_id}
    if details is not None:
        payload["error"]["details"] = details
    return payload

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content=_error_payload("validation_error", "Request validation failed", request_id, details={"errors": exc.errors()}),
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload("http_error", str(exc.detail), request_id),
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=_error_payload("internal_error", "Internal server error", request_id),
    )

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev/demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper Functions
def get_workspace_root() -> Path:
    configured_root = os.getenv("WINDOW_AICHAT_WORKSPACE_ROOT")
    return Path(configured_root or os.getcwd()).resolve()

def get_safe_path(path: str) -> Path:
    """Resolve path and ensure it's within the allowed directory."""
    root = get_workspace_root()
    raw = Path(path)
    if raw.is_absolute() or raw.drive:
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed")
    requested = (root / raw).resolve()
    try:
        requested.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    return requested

def get_ai_client(gemini_key: str = None, deepseek_key: str = None):
    """Create or configure an AI client on the fly."""
    if not AI_CORE_AVAILABLE:
        raise HTTPException(status_code=500, detail="AI Core not available")

    # Create a dummy config path since we are overriding keys anyway
    # Use a safe path for config
    config_path = os.path.abspath("dummy_config.json")
    client = AIChatClient(config_path)

    # Override keys in the config
    if gemini_key:
        client.config["gemini_api_key"] = gemini_key
    if deepseek_key:
        client.config["deepseek_api_key"] = deepseek_key
        
    # Re-configure APIs with new keys
    client.configure_apis()
    return client

# V2 Auth + Persistence Endpoints

class AuthRegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=512)


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str


class SessionCreateRequest(BaseModel):
    name: str = "New Session"
    model: str = "gemini"
    pinnedFiles: List[str] = Field(default_factory=list)


class SessionUpdateRequest(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    pinnedFiles: Optional[List[str]] = None
    messages: Optional[List[ChatMessage]] = None


class EmbeddingUpsertRequest(BaseModel):
    namespace: str
    ref: str
    content: str
    vector: List[float]


class EmbeddingSearchRequest(BaseModel):
    namespace: str
    vector: List[float]
    topK: int = 8


class MemoryUpsertRequest(BaseModel):
    kind: str
    key: str
    value: str
    source: Optional[str] = None
    confidence: float = 0.7


MODEL_CAPABILITIES = {
    "gemini": {"maxTokens": 8192, "streaming": True, "strengths": ["latency", "general"]},
    "deepseek": {"maxTokens": 8192, "streaming": True, "strengths": ["coding", "reasoning"]},
}


@app.post("/api/auth/register", response_model=AuthResponse)
async def auth_register(req: AuthRegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.username == req.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=req.username, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(token=issue_token(user.id, user.username))


@app.post("/api/auth/login", response_model=AuthResponse)
async def auth_login(req: AuthLoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.username == req.username)).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return AuthResponse(token=issue_token(user.id, user.username))


@app.get("/api/sessions")
async def list_sessions(user: User = Depends(require_user), db: Session = Depends(get_db)):
    sessions = db.execute(
        select(ProjectSession).where(ProjectSession.user_id == user.id).order_by(ProjectSession.updated_at.desc())
    ).scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "model": s.model,
            "pinnedFiles": s.pinned_files(),
            "updatedAt": s.updated_at.isoformat(),
        }
        for s in sessions
    ]


@app.post("/api/sessions")
async def create_session(req: SessionCreateRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = ProjectSession(user_id=user.id, name=req.name, model=req.model)
    s.set_pinned_files(req.pinnedFiles)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(ProjectSession, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    msgs = db.execute(select(SessionMessage).where(SessionMessage.session_id == s.id).order_by(SessionMessage.created_at.asc())).scalars().all()
    return {
        "id": s.id,
        "name": s.name,
        "model": s.model,
        "pinnedFiles": s.pinned_files(),
        "messages": [{"role": m.role, "content": m.content} for m in msgs],
        "updatedAt": s.updated_at.isoformat(),
    }


@app.put("/api/sessions/{session_id}")
async def update_session(session_id: str, req: SessionUpdateRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(ProjectSession, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if req.name is not None:
        s.name = req.name
    if req.model is not None:
        s.model = req.model
    if req.pinnedFiles is not None:
        s.set_pinned_files(req.pinnedFiles)
    if req.messages is not None:
        db.execute(delete(SessionMessage).where(SessionMessage.session_id == s.id))
        for m in req.messages:
            db.add(SessionMessage(session_id=s.id, role=m.role, content=m.content))
    s.updated_at = datetime.now(timezone.utc)
    db.add(s)
    db.commit()
    return {"status": "ok"}


@app.get("/api/memory")
async def list_memory(user: User = Depends(require_user), db: Session = Depends(get_db)):
    items = db.execute(select(MemoryItem).where(MemoryItem.user_id == user.id).order_by(MemoryItem.updated_at.desc())).scalars().all()
    return [
        {
            "id": m.id,
            "kind": m.kind,
            "key": m.key,
            "value": m.value,
            "source": m.source,
            "confidence": m.confidence,
            "createdAt": m.created_at.isoformat(),
            "updatedAt": m.updated_at.isoformat(),
        }
        for m in items
    ]


@app.post("/api/memory")
async def upsert_memory(req: MemoryUpsertRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    existing = db.execute(select(MemoryItem).where(MemoryItem.user_id == user.id, MemoryItem.kind == req.kind, MemoryItem.key == req.key)).scalar_one_or_none()
    if existing:
        existing.value = req.value
        existing.source = req.source
        existing.confidence = float(req.confidence)
        existing.updated_at = datetime.now(timezone.utc)
        db.add(existing)
        db.commit()
        return {"status": "updated", "id": existing.id}
    item = MemoryItem(user_id=user.id, kind=req.kind, key=req.key, value=req.value, source=req.source, confidence=float(req.confidence))
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"status": "created", "id": item.id}


@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    item = db.get(MemoryItem, memory_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted"}


@app.get("/api/audit")
async def list_audit(user: User = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.execute(select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc()).limit(100)).scalars().all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "path": r.path,
            "bytes": r.bytes,
            "requestId": r.request_id,
            "ip": r.ip,
            "createdAt": r.created_at.isoformat(),
        }
        for r in rows
    ]


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return -1.0
    return dot / (na * nb)


@app.post("/api/embeddings/upsert")
async def upsert_embedding(req: EmbeddingUpsertRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not req.vector:
        raise HTTPException(status_code=400, detail="Empty vector")
    existing = db.execute(
        select(EmbeddingItem).where(
            EmbeddingItem.user_id == user.id,
            EmbeddingItem.namespace == req.namespace,
            EmbeddingItem.ref == req.ref,
        )
    ).scalar_one_or_none()
    if existing:
        existing.content = req.content
        existing.set_vector(req.vector)
        db.add(existing)
        db.commit()
        return {"status": "updated", "id": existing.id}
    item = EmbeddingItem(user_id=user.id, namespace=req.namespace, ref=req.ref, content=req.content, vector_json="[]", dims=0)
    item.set_vector(req.vector)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"status": "created", "id": item.id}


@app.post("/api/embeddings/search")
async def search_embeddings(req: EmbeddingSearchRequest, user: User = Depends(require_user), db: Session = Depends(get_db)):
    top_k = max(1, min(int(req.topK), 50))
    rows = db.execute(
        select(EmbeddingItem).where(EmbeddingItem.user_id == user.id, EmbeddingItem.namespace == req.namespace)
    ).scalars().all()
    scored = []
    for r in rows:
        vec = r.vector()
        if len(vec) != len(req.vector):
            continue
        scored.append((r, _cosine(req.vector, vec)))
    scored.sort(key=lambda t: t[1], reverse=True)
    out = []
    for r, score in scored[:top_k]:
        out.append({"ref": r.ref, "content": r.content, "score": score})
    return {"results": out}


@app.get("/api/models")
async def list_models():
    return {"models": MODEL_CAPABILITIES}

# Endpoints

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    current_cancel: Optional[threading.Event] = None
    current_task: Optional[asyncio.Task] = None

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": {"code": "invalid_json", "message": "Invalid JSON"}})
                continue

            msg_type = payload.get("type", "start")
            if msg_type == "cancel":
                if current_cancel is not None:
                    current_cancel.set()
                if current_task is not None:
                    current_task.cancel()
                await websocket.send_json({"type": "cancelled"})
                continue

            if msg_type != "start":
                await websocket.send_json({"type": "error", "error": {"code": "invalid_type", "message": "Unknown message type"}})
                continue

            message = payload.get("message")
            if not message:
                await websocket.send_json({"type": "error", "error": {"code": "empty_message", "message": "Empty message"}})
                continue

            model = payload.get("model", "gemini")
            history = payload.get("history", [])
            gemini_key = payload.get("gemini_key")
            deepseek_key = payload.get("deepseek_key")

            if not AI_CORE_AVAILABLE:
                await websocket.send_json({"type": "error", "error": {"code": "ai_unavailable", "message": "AI features unavailable"}})
                continue

            try:
                client = get_ai_client(gemini_key, deepseek_key)
            except Exception:
                logger.error("Error initializing client", exc_info=True)
                await websocket.send_json({"type": "error", "error": {"code": "init_failed", "message": "Failed to initialize AI client"}})
                continue

            history_dicts: List[Dict[str, str]] = []
            for msg in history:
                if isinstance(msg, dict):
                    history_dicts.append({"role": str(msg.get("role", "user")), "content": str(msg.get("content", ""))})
            full_prompt = build_prompt_from_history(history_dicts, str(message))

            if current_cancel is not None:
                current_cancel.set()
            if current_task is not None:
                current_task.cancel()

            request_id = uuid.uuid4().hex
            cancel_flag = threading.Event()
            current_cancel = cancel_flag

            await websocket.send_json({"type": "start", "requestId": request_id})

            async def _run_stream():
                loop = asyncio.get_running_loop()
                q: asyncio.Queue = asyncio.Queue()

                def _producer():
                    try:
                        for chunk in client.stream_chat(full_prompt, model):
                            if cancel_flag.is_set():
                                break
                            asyncio.run_coroutine_threadsafe(q.put({"type": "chunk", "content": chunk}), loop)
                        asyncio.run_coroutine_threadsafe(q.put({"type": "done"}), loop)
                    except Exception:
                        logger.error("Streaming error", exc_info=True)
                        asyncio.run_coroutine_threadsafe(
                            q.put({"type": "error", "error": {"code": "stream_failed", "message": "Streaming failed"}}),
                            loop,
                        )

                threading.Thread(target=_producer, daemon=True).start()

                while True:
                    item = await q.get()
                    await websocket.send_json(item)
                    if item.get("type") in {"done", "error"}:
                        break

            current_task = asyncio.create_task(_run_stream())
            try:
                await current_task
            except asyncio.CancelledError:
                pass
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


@app.websocket("/ws/tools")
async def websocket_tools(websocket: WebSocket):
    await websocket.accept()
    current_cancel: Optional[threading.Event] = None
    current_task: Optional[asyncio.Task] = None

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "tool", "stage": "error", "message": "Invalid JSON"})
                continue

            msg_type = payload.get("type", "run")
            if msg_type == "cancel":
                if current_cancel is not None:
                    current_cancel.set()
                if current_task is not None:
                    current_task.cancel()
                await websocket.send_json({"type": "tool", "stage": "cancelled", "message": "Cancelled"})
                continue

            if msg_type != "run":
                await websocket.send_json({"type": "tool", "stage": "error", "message": "Unknown message type"})
                continue

            tool = payload.get("tool", "analyze")
            code = payload.get("code", "")
            gemini_key = payload.get("gemini_key")
            deepseek_key = payload.get("deepseek_key")

            if not AI_CORE_AVAILABLE:
                await websocket.send_json({"type": "tool", "stage": "error", "message": "AI features unavailable"})
                continue

            try:
                client = get_ai_client(gemini_key, deepseek_key)
            except Exception:
                logger.error("Error initializing client", exc_info=True)
                await websocket.send_json({"type": "tool", "stage": "error", "message": "Failed to initialize AI client"})
                continue

            prompt = ""
            if tool == "analyze":
                prompt = f"Analyze the following code and provide insights:\n\n{code}"
            elif tool == "explain":
                prompt = f"Explain the following code in simple terms:\n\n{code}"
            elif tool == "refactor":
                prompt = f"Refactor the following code to improve quality and readability:\n\n{code}"
            elif tool == "docs":
                prompt = f"Generate documentation for the following code:\n\n{code}"
            else:
                prompt = f"Perform task '{tool}' on the following code:\n\n{code}"

            if current_cancel is not None:
                current_cancel.set()
            if current_task is not None:
                current_task.cancel()

            cancel_flag = threading.Event()
            current_cancel = cancel_flag

            await websocket.send_json({"type": "tool", "stage": "start", "message": f"Running tool: {tool}", "progress": 0})

            async def _run_stream():
                loop = asyncio.get_running_loop()
                q: asyncio.Queue = asyncio.Queue()

                def _producer():
                    try:
                        model_name = "gemini" if client.gemini_available else "deepseek"
                        for chunk in client.stream_chat(prompt, model_name):
                            if cancel_flag.is_set():
                                break
                            asyncio.run_coroutine_threadsafe(
                                q.put({"type": "tool", "stage": "output", "message": chunk}), loop
                            )
                        asyncio.run_coroutine_threadsafe(q.put({"type": "tool", "stage": "done", "message": "Done", "progress": 1}), loop)
                    except Exception:
                        logger.error("Tool streaming error", exc_info=True)
                        asyncio.run_coroutine_threadsafe(
                            q.put({"type": "tool", "stage": "error", "message": "Tool run failed"}), loop
                        )

                threading.Thread(target=_producer, daemon=True).start()

                while True:
                    item = await q.get()
                    await websocket.send_json(item)
                    if item.get("stage") in {"done", "error"}:
                        break

            current_task = asyncio.create_task(_run_stream())
            try:
                await current_task
            except asyncio.CancelledError:
                pass
    except WebSocketDisconnect:
        logger.info("Tools WebSocket disconnected")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not AI_CORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI features unavailable")
        
    client = get_ai_client(request.gemini_key, request.deepseek_key)
    
    history_dicts: List[Dict[str, str]] = [{"role": msg.role, "content": msg.content} for msg in request.history]
    full_prompt = build_prompt_from_history(history_dicts, request.message)
    
    try:
        requested = (request.model or "gemini").lower()
        candidates: List[str] = []
        if requested in {"auto", "router"}:
            candidates = ["deepseek", "gemini"]
        else:
            candidates = [requested, "gemini", "deepseek"]

        tried: List[str] = []
        for model_name in candidates:
            if model_name == "gemini" and not client.gemini_available:
                continue
            if model_name == "deepseek" and not client.deepseek_available:
                continue
            tried.append(model_name)
            response = client.ask_deepseek(full_prompt) if model_name == "deepseek" else client.ask_gemini(full_prompt)
            if isinstance(response, str) and response.startswith("Error:"):
                continue
            return ChatResponse(content=response, model=model_name)

        detail_msg = "No AI model available."
        if tried:
            detail_msg = f"All models failed: {', '.join(tried)}"
        if not client.gemini_available:
            detail_msg += f" Gemini Error: {client.gemini_error}"
        if not client.deepseek_available:
            detail_msg += f" DeepSeek Error: {client.deepseek_error}"
        raise HTTPException(status_code=400, detail=detail_msg)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise

@app.post("/api/completion")
async def completion(request: CompletionRequest):
    if not AI_CORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI features unavailable")
        
    client = get_ai_client(request.gemini_key, request.deepseek_key)
    
    prompt = f"""
    Complete the following {request.language} code at position {request.position}.
    Only return the code to insert, no markdown or explanations.
    
    Code:
    {request.code}
    """
    
    try:
        if client.gemini_available:
            result = client.ask_gemini(prompt)
            result = result.replace("```python", "").replace("```", "").strip()
            return CompletionResponse(completion=result)
        else:
             raise HTTPException(status_code=503, detail="Gemini not available for completion")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Completion error: {e}")
        raise

@app.post("/api/git/clone")
async def git_clone(request: CloneRequest):
    try:
        import subprocess
        
        target = request.target_dir or request.repo_url.split("/")[-1].replace(".git", "")
        safe_target = get_safe_path(target)
        
        if safe_target.exists():
             raise HTTPException(status_code=400, detail="Directory already exists")
             
        # Run git clone
        process = subprocess.run(
            ["git", "clone", request.repo_url, str(safe_target)],
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Git clone failed: {process.stderr}")
            
        return CloneResponse(status="success", path=str(safe_target))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clone error: {e}")
        raise

@app.get("/health")
async def health_check():
    return {"status": "ok", "backend": "fastapi"}

@app.get("/api/fs/list")
async def list_files():
    """List all files in the project workspace."""
    files = []
    root = get_workspace_root()
    
    exclude_dirs = {'.git', 'venv', '__pycache__', 'node_modules', '.next', '.vercel', 'window_aichat'} 
    
    for root_dir, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for name in filenames:
            file_path = Path(root_dir) / name
            try:
                rel_path = file_path.relative_to(root)
                files.append({
                    "name": name,
                    "type": "file",
                    "path": str(rel_path).replace("\\", "/")
                })
            except ValueError:
                continue
                
    return files

from fastapi.staticfiles import StaticFiles

# Mount static files (Frontend) if available
# This should be placed after API routes to avoid conflicts
static_path = Path("static")
if static_path.exists() and static_path.is_dir():
    logger.info(f"Serving static files from {static_path.absolute()}")
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
else:
    logger.warning("Static directory not found, running in API-only mode.")


@app.post("/api/fs/read")
async def read_file(request: FileReadRequest):
    try:
        file_path = get_safe_path(request.path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")
            
        try:
            content = file_path.read_text(encoding="utf-8")
            return FileReadResponse(content=content)
        except UnicodeDecodeError:
            return FileReadResponse(content="Binary file content not displayed.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise

@app.post("/api/fs/write")
async def write_file(
    request: FileWriteRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    try:
        if _require_auth and user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        file_path = get_safe_path(request.path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(request.content, encoding="utf-8")
        try:
            db.add(
                AuditLog(
                    user_id=user.id if user else None,
                    action="fs_write",
                    path=str(file_path),
                    bytes=len(request.content.encode("utf-8")),
                    request_id=getattr(http_request.state, "request_id", None),
                    ip=_get_request_ip(http_request),
                )
            )
            db.commit()
        except Exception:
            db.rollback()
        return FileWriteResponse(status="success", path=str(file_path))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error writing file: {e}")
        raise

@app.post("/api/fs/upload")
async def upload_file(
    http_request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user),
):
    try:
        if _require_auth and user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        filename = Path(file.filename or "upload.bin").name
        target_path = get_safe_path(str(Path("uploads") / filename))
        target_path.parent.mkdir(parents=True, exist_ok=True)

        import aiofiles

        async with aiofiles.open(target_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                await f.write(chunk)

        try:
            db.add(
                AuditLog(
                    user_id=user.id if user else None,
                    action="fs_upload",
                    path=str(target_path),
                    bytes=int(target_path.stat().st_size) if target_path.exists() else 0,
                    request_id=getattr(http_request.state, "request_id", None),
                    ip=_get_request_ip(http_request),
                )
            )
            db.commit()
        except Exception:
            db.rollback()
        return FileWriteResponse(status="success", path=str(target_path))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise

@app.post("/api/tool")
async def run_tool(request: ToolRequest):
    if not AI_CORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI features unavailable")
        
    client = get_ai_client(request.gemini_key, request.deepseek_key)
    
    prompt = ""
    if request.tool == "analyze":
        prompt = f"Analyze the following code and provide insights:\n\n{request.code}"
    elif request.tool == "explain":
        prompt = f"Explain the following code in simple terms:\n\n{request.code}"
    elif request.tool == "refactor":
        prompt = f"Refactor the following code to improve quality and readability:\n\n{request.code}"
    elif request.tool == "docs":
        prompt = f"Generate documentation for the following code:\n\n{request.code}"
    else:
        prompt = f"Perform task '{request.tool}' on the following code:\n\n{request.code}"
        
    if client.gemini_available:
        result = client.ask_gemini(prompt)
    elif client.deepseek_available:
        result = client.ask_deepseek(prompt)
    else:
        raise HTTPException(status_code=400, detail="No valid API key provided. Please configure settings.")
        
    return {"result": result}

@app.post("/api/system/open-vscode")
async def open_vscode(request: VSCodeRequest):
    try:
        file_path = get_safe_path(request.path)
        os.system(f"code \"{file_path}\"")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error opening VS Code: {e}")
        return {"status": "ignored", "message": "Server-side VS Code open not supported"}

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_config():
    """Silence Chrome DevTools 404 errors."""
    return JSONResponse(content={})

# Serve static files if "static" directory exists (for Docker/Production)
static_dir = Path(os.getcwd()) / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
