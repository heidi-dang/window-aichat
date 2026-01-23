import os

import sys

import logging

import glob

from pathlib import Path

from typing import Optional, List, Dict, Any



from fastapi import FastAPI, HTTPException, Body, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse

from pydantic import BaseModel

import uvicorn



# Ensure local modules can be imported

sys.path.append(os.path.dirname(os.path.abspath(__file__)))



# Try importing core modules; handle failures gracefully

try:

    from ai_core import AIChatClient

    AI_CORE_AVAILABLE = True

except ImportError:

    AI_CORE_AVAILABLE = False

    print("Warning: ai_core module not found. AI features will be limited.")



# Setup logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("backend")



app = FastAPI(title="Window AI Chat Backend")



# CORS Configuration

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],  # Allow all origins for dev/demo

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



# Data Models

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



# Helper Functions

def get_safe_path(path: str) -> Path:

    """Resolve path and ensure it's within the allowed directory."""

    # For this project, we treat the current working directory as the root

    root = Path(os.getcwd()).resolve()

    requested = (root / path).resolve()

    

    # Simple check to prevent escaping root (though we allow it for this IDE tool)

    # if not str(requested).startswith(str(root)):

    #     raise HTTPException(status_code=403, detail="Access denied")

    

    return requested



def get_ai_client(gemini_key: str = None, deepseek_key: str = None):

    """Create or configure an AI client on the fly."""

    if not AI_CORE_AVAILABLE:

        raise HTTPException(status_code=500, detail="AI Core not available")

    

    # Create a dummy config path since we are overriding keys anyway

    client = AIChatClient("dummy_config.json")

    

    # Override keys in the config

    if gemini_key:

        client.config["gemini_api_key"] = gemini_key

    if deepseek_key:

        client.config["deepseek_api_key"] = deepseek_key

        

    # Re-configure APIs with new keys

    client.configure_apis()

    return client



# Endpoints



@app.post("/api/chat")

async def chat(request: ChatRequest):

    if not AI_CORE_AVAILABLE:

        raise HTTPException(status_code=503, detail="AI features unavailable")

        

    client = get_ai_client(request.gemini_key, request.deepseek_key)

    

    # Format history for the client if needed, or just use the prompt

    # Simple implementation: Concatenate history + message

    full_prompt = ""

    for msg in request.history:

        role = msg.get("role", "user")

        content = msg.get("content", "")

        full_prompt += f"{role}: {content}\n"

    full_prompt += f"user: {request.message}\n"

    

    try:
        if request.model == "deepseek" and client.deepseek_available:
            response = client.ask_deepseek(full_prompt)
            return {"role": "assistant", "content": response, "model": "deepseek"}
        elif client.gemini_available:
            # Gemini might have a dedicated chat method, but ask_gemini works for now
            response = client.ask_gemini(full_prompt)
            return {"role": "assistant", "content": response, "model": "gemini"}
        else:
            # If no model is available, check why
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
        raise HTTPException(status_code=500, detail=str(e))



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

            # Cleanup result to be just code

            result = result.replace("```python", "").replace("```", "").strip()

            return {"completion": result}

        else:
             raise HTTPException(status_code=503, detail="Gemini not available for completion")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



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

            

        return {"status": "success", "path": str(safe_target)}

    except Exception as e:

        logger.error(f"Clone error: {e}")

        raise HTTPException(status_code=500, detail=str(e))



@app.get("/health")

async def health_check():

    return {"status": "ok", "backend": "fastapi"}



@app.get("/api/fs/list")

async def list_files():

    """List all files in the project workspace."""

    files = []

    root = Path(os.getcwd())

    

    # Exclude patterns

    exclude_dirs = {'.git', 'venv', '__pycache__', 'node_modules', '.next', '.vercel'}

    

    for root_dir, dirs, filenames in os.walk(root):

        # Filter directories in place

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

            return {"content": content}

        except UnicodeDecodeError:

            return {"content": "Binary file content not displayed."}

            

    except Exception as e:

        logger.error(f"Error reading file: {e}")

        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/fs/write")

async def write_file(request: FileWriteRequest):

    try:

        file_path = get_safe_path(request.path)

        # Create parent directories if needed

        file_path.parent.mkdir(parents=True, exist_ok=True)

        

        file_path.write_text(request.content, encoding="utf-8")

        return {"status": "success", "path": str(file_path)}

    except Exception as e:

        logger.error(f"Error writing file: {e}")

        raise HTTPException(status_code=500, detail=str(e))



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

        

    # Use Gemini by default if available, else DeepSeek

    if client.gemini_available:

        result = client.ask_gemini(prompt)

    elif client.deepseek_available:

        result = client.ask_deepseek(prompt)

    else:

        return JSONResponse(

            status_code=400, 

            content={"error": "No valid API key provided. Please configure settings."}

        )

        

    return {"result": result}



@app.post("/api/system/open-vscode")

async def open_vscode(request: VSCodeRequest):

    # This only works in local environment

    try:

        file_path = get_safe_path(request.path)

        os.system(f"code \"{file_path}\"")

        return {"status": "success"}

    except Exception as e:

        logger.error(f"Error opening VS Code: {e}")

        # Don't fail the request, just log it (it's expected to fail in cloud)

        return {"status": "ignored", "message": "Server-side VS Code open not supported"}



@app.get("/.well-known/appspecific/com.chrome.devtools.json")

async def chrome_devtools_config():

    """Silence Chrome DevTools 404 errors."""

    return JSONResponse(content={})



if __name__ == "__main__":

    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)

