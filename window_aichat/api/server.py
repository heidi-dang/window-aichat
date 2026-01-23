import os
import sys
import logging
import json
import uuid
import asyncio
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

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
    ChatRequest,
    ChatResponse,
    CompletionRequest,
    CompletionResponse,
    CloneRequest,
    CloneResponse,
    FileReadResponse,
    FileWriteResponse,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("window_aichat.api.server")

app = FastAPI(title="Window AI Chat Backend")

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

            full_prompt = ""
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                full_prompt += f"{role}: {content}\n"
            full_prompt += f"user: {message}\n"

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

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not AI_CORE_AVAILABLE:
        raise HTTPException(status_code=503, detail="AI features unavailable")
        
    client = get_ai_client(request.gemini_key, request.deepseek_key)
    
    # Format history for the client
    full_prompt = ""
    for msg in request.history:
        full_prompt += f"{msg.role}: {msg.content}\n"
    full_prompt += f"user: {request.message}\n"
    
    try:
        if request.model == "deepseek" and client.deepseek_available:
            response = client.ask_deepseek(full_prompt)
            return ChatResponse(content=response, model="deepseek")
        elif client.gemini_available:
            response = client.ask_gemini(full_prompt)
            return ChatResponse(content=response, model="gemini")
        else:
            detail_msg = "No AI model available."
            if not client.gemini_available:
                detail_msg += f" Gemini Error: {client.gemini_error}"
            if request.model == "deepseek" and not client.deepseek_available:
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
async def write_file(request: FileWriteRequest):
    try:
        file_path = get_safe_path(request.path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(request.content, encoding="utf-8")
        return FileWriteResponse(status="success", path=str(file_path))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error writing file: {e}")
        raise

@app.post("/api/fs/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
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
