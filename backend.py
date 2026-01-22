import os
import sys
import logging
import subprocess
import asyncio
import shutil
import zipfile
from typing import Optional
from unittest.mock import MagicMock

import psutil
from fastapi import (
    FastAPI,
    HTTPException,
    Body,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- 2. Import Existing Logic ---
# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_core import AIChatClient
    from github_handler import GitHubHandler
except ImportError as e:
    print(f"Error importing existing logic: {e}")
    sys.exit(1)

# --- 3. App Configuration ---
app = FastAPI(title="AI Chat Backend")

# Configure CORS to allow requests from the React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Cache Directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "server_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
# Workspace for Web App Files
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)


# --- 4. Data Models ---
class ChatRequest(BaseModel):
    message: str
    model: str = "both"
    repo_url: Optional[str] = ""
    gemini_key: Optional[str] = ""
    deepseek_key: Optional[str] = ""
    github_token: Optional[str] = ""


class ChatResponse(BaseModel):
    sender: str
    text: str
    timestamp: str


class FileReadRequest(BaseModel):
    path: str


class FileWriteRequest(BaseModel):
    path: str
    content: str


class ToolRequest(BaseModel):
    tool: str
    code: str
    gemini_key: Optional[str] = ""


class CloneRequest(BaseModel):
    repo_url: str


# --- 5. Helper Functions ---
def get_ai_client(req: ChatRequest) -> AIChatClient:
    """
    Instantiate AIChatClient and inject keys from the request.
    This makes the backend stateless regarding user API keys.
    """
    # Initialize with a dummy config path to avoid reading local desktop config
    dummy_config = os.path.join(CACHE_DIR, "dummy_config.json")
    client = AIChatClient(dummy_config)

    # Inject keys from request
    client.config = {
        "gemini_api_key": req.gemini_key,
        "deepseek_api_key": req.deepseek_key,
        "gemini_model": "gemini-2.0-flash",  # Default
    }

    # Re-configure APIs with new keys
    client.configure_apis()
    return client


def get_repo_context(repo_url: str, token: Optional[str]) -> str:
    if not repo_url:
        return ""

    handler = GitHubHandler(os.path.join(CACHE_DIR, "repo_cache"), token=token)
    context = handler.fetch_repo_context(repo_url)

    if context.startswith("Error"):
        logging.error(f"GitHub Error: {context}")
        return ""
    return context


def get_tool_prompt(tool: str, code: str) -> str:
    prompts = {
        "analyze": f"Analyze this code for bugs, performance, and security:\n\n{code}",
        "docs": f"Generate documentation for this code:\n\n{code}",
        "refactor": f"Refactor this code to improve quality and readability:\n\n{code}",
        "security": f"Check this code for security vulnerabilities:\n\n{code}",
        "tests": f"Generate unit tests for this code:\n\n{code}",
        "explain": f"Explain how this code works:\n\n{code}",
        "optimize": f"Suggest optimizations for this code:\n\n{code}",
    }
    return prompts.get(tool, f"Analyze this code:\n\n{code}")


# --- 6. API Endpoints ---
@app.get("/")
async def health_check():
    return {"status": "ok", "service": "AI Chat Backend"}


@app.get("/api/processes")
async def list_processes():
    processes = []
    for proc in psutil.process_iter(
        ["pid", "name", "username", "cpu_percent", "memory_info"]
    ):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        # 1. Fetch Context (if repo provided)
        context = get_repo_context(req.repo_url, req.github_token)

        # 2. Construct Prompt
        full_prompt = req.message
        if context:
            full_prompt = f"Context from GitHub Repository:\n{context}\n\nUser Query:\n{req.message}"

        # 3. Initialize Client
        client = get_ai_client(req)

        # 4. Call AI Models
        response_text = ""
        sender = "AI"

        if req.model == "gemini":
            response_text = client.ask_gemini(full_prompt)
            sender = "Gemini"
        elif req.model == "deepseek":
            response_text = client.ask_deepseek(full_prompt)
            sender = "DeepSeek"
        else:
            # For 'both', we just return Gemini for simplicity in this REST endpoint,
            # or you could modify the frontend to handle a JSON object with both.
            # Here we combine them textually.
            responses = client.ask_both(full_prompt)
            response_text = f"**Gemini:**\n{responses['gemini']}\n\n---\n\n**DeepSeek:**\n{responses['deepseek']}"
            sender = "Gemini & DeepSeek"

        from datetime import datetime

        return {
            "sender": sender,
            "text": response_text,
            "timestamp": datetime.now().strftime("%H:%M"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fs/list")
async def list_files():
    files = []
    for root, dirs, filenames in os.walk(WORKSPACE_DIR):
        rel_path = os.path.relpath(root, WORKSPACE_DIR)
        if rel_path == ".":
            rel_path = ""

        for d in dirs:
            files.append(
                {
                    "name": d,
                    "type": "directory",
                    "path": os.path.join(rel_path, d).replace("\\", "/"),
                }
            )
        for f in filenames:
            files.append(
                {
                    "name": f,
                    "type": "file",
                    "path": os.path.join(rel_path, f).replace("\\", "/"),
                }
            )
    return files


@app.post("/api/fs/read")
async def read_file(req: FileReadRequest):
    safe_path = os.path.normpath(os.path.join(WORKSPACE_DIR, req.path))
    if not safe_path.startswith(WORKSPACE_DIR):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fs/write")
async def write_file(req: FileWriteRequest):
    safe_path = os.path.normpath(os.path.join(WORKSPACE_DIR, req.path))
    if not safe_path.startswith(WORKSPACE_DIR):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tool")
async def run_tool(req: ToolRequest):
    # Create a temporary client using the key provided in request (or default)
    client = get_ai_client(ChatRequest(message="", gemini_key=req.gemini_key))
    prompt = get_tool_prompt(req.tool, req.code)
    result = client.ask_gemini(prompt)
    return {"result": result}


@app.post("/api/git/clone")
async def clone_repo(req: CloneRequest):
    try:
        # Extract repo name
        repo_name = req.repo_url.split("/")[-1].replace(".git", "")
        target_dir = os.path.join(WORKSPACE_DIR, repo_name)

        if os.path.exists(target_dir):
            return {
                "status": "exists",
                "message": f"Repository '{repo_name}' already exists in workspace.",
            }

        # Run git clone
        process = subprocess.run(
            ["git", "clone", req.repo_url, target_dir], capture_output=True, text=True
        )

        if process.returncode != 0:
            raise Exception(f"Git clone failed: {process.stderr}")

        return {"status": "ok", "message": f"Cloned '{repo_name}' successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fs/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(WORKSPACE_DIR, file.filename)

        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # If zip, extract it
        if file.filename.endswith(".zip"):
            extract_dir = os.path.join(
                WORKSPACE_DIR, os.path.splitext(file.filename)[0]
            )
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            os.remove(file_path)  # Remove zip after extraction
            return {
                "status": "ok",
                "message": f"Uploaded and extracted '{file.filename}'.",
            }

        return {"status": "ok", "message": f"Uploaded '{file.filename}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Terminal Endpoint (WebSocket) ---
@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    await websocket.accept()

    # Check for PTY support (Linux/macOS only)
    try:
        import pty
    except ImportError:
        if os.name == "nt":
            # Windows Fallback using asyncio subprocess
            try:
                shell = os.environ.get("COMSPEC", "cmd.exe")
                process = await asyncio.create_subprocess_shell(
                    shell,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                async def read_stream(stream):
                    try:
                        while True:
                            data = await stream.read(1024)
                            if not data:
                                break
                            try:
                                text = data.decode("cp437")
                            except:
                                text = data.decode("utf-8", errors="ignore")
                            await websocket.send_text(text)
                    except:
                        pass

                asyncio.create_task(read_stream(process.stdout))
                asyncio.create_task(read_stream(process.stderr))

                try:
                    while True:
                        data = await websocket.receive_text()
                        process.stdin.write(data.encode())
                        await process.stdin.drain()
                except WebSocketDisconnect:
                    pass
                finally:
                    try:
                        process.terminate()
                    except:
                        pass
                return
            except Exception as e:
                await websocket.send_text(f"Error starting Windows terminal: {e}\r\n")
                await websocket.close()
                return
        else:
            await websocket.send_text(
                "Error: Backend terminal requires Linux/macOS (pty module missing).\r\n"
            )
            await websocket.close()
            return

    # Spawn Shell with TERM environment variable for colors
    master_fd, slave_fd = pty.openpty()
    shell = os.environ.get("SHELL", "/bin/bash")

    # Important: Set TERM so tools know to output color
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"

    process = subprocess.Popen(
        [shell],
        preexec_fn=os.setsid,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        universal_newlines=True,
        env=env,
    )

    os.close(slave_fd)  # Close slave in parent

    loop = asyncio.get_running_loop()

    async def send_output():
        try:
            # Read from PTY and send to WebSocket
            output = await loop.run_in_executor(None, lambda: os.read(master_fd, 10240))
            if output:
                await websocket.send_text(output.decode(errors="ignore"))
            else:
                # EOF
                await websocket.close()
        except Exception:
            pass

    # Register reader for PTY output
    loop.add_reader(master_fd, lambda: asyncio.create_task(send_output()))

    try:
        while True:
            # Receive from WebSocket and write to PTY
            data = await websocket.receive_text()
            os.write(master_fd, data.encode())
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Terminal error: {e}")
    finally:
        loop.remove_reader(master_fd)
        process.kill()
        os.close(master_fd)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
