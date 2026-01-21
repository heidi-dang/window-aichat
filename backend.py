import os
import sys
import logging
import subprocess
import asyncio
from typing import Optional
from unittest.mock import MagicMock

# --- 1. Headless Environment Setup ---
# Mock tkinter modules to prevent ImportErrors when importing main.py on a server
sys.modules["tkinter"] = MagicMock()
sys.modules["tkinter.scrolledtext"] = MagicMock()
sys.modules["tkinter.ttk"] = MagicMock()
sys.modules["tkinter.messagebox"] = MagicMock()
sys.modules["tkinter.filedialog"] = MagicMock()
sys.modules["tkinter.simpledialog"] = MagicMock()

from fastapi import FastAPI, HTTPException, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- 2. Import Existing Logic ---
# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main import AIChatClient
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
        "gemini_model": "gemini-2.0-flash" # Default
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

# --- 6. API Endpoints ---
@app.get("/")
async def health_check():
    return {"status": "ok", "service": "AI Chat Backend"}

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
            "timestamp": datetime.now().strftime("%H:%M")
        }

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
        await websocket.send_text("Error: Backend terminal requires Linux/macOS (pty module missing).\r\n")
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
        env=env
    )
    
    os.close(slave_fd) # Close slave in parent

    loop = asyncio.get_running_loop()

    async def send_output():
        try:
            # Read from PTY and send to WebSocket
            output = await loop.run_in_executor(None, lambda: os.read(master_fd, 10240))
            if output:
                await websocket.send_text(output.decode(errors='ignore'))
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