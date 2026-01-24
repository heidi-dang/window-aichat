import os
import sys
import logging
import subprocess
import asyncio
import shutil
import time
import zipfile
import secrets
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import psutil
import httpx
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from jose import jwt, JWTError
from fastapi import (
    FastAPI,
    HTTPException,
    Body,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Depends,
    Request,
    Query,
)
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- 2. Import Existing Logic ---
# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_core import AIChatClient
    from github_handler import GitHubHandler
except ImportError as e:
    logger.error(f"Error importing existing logic: {e}")
    sys.exit(1)

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

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

# --- 3.1 Database Setup (SQLite) ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./aichat.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- 3.2 Database Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    provider = Column(String)  # google, github, apple
    provider_id = Column(String, index=True)
    created_at = Column(
        DateTime, default=datetime.now
    )  # Corrected to datetime.now (callable)

    chats = relationship("ChatMessage", back_populates="user")
    files = relationship("FileRecord", back_populates="user")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    sender = Column(String)
    text = Column(Text)
    timestamp = Column(
        DateTime, default=datetime.now
    )  # Corrected to datetime.now (callable)

    user = relationship("User", back_populates="chats")


class FileRecord(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    file_path = Column(String)
    uploaded_at = Column(
        DateTime, default=datetime.now
    )  # Corrected to datetime.now (callable)

    user = relationship("User", back_populates="files")


# Create Tables
Base.metadata.create_all(bind=engine)

# --- 3.3 Auth Configuration ---
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# OAuth Configs (Load from env)
OAUTH_CONFIG = {
    "google": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
    },
    "github": {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_info_url": "https://api.github.com/user",
        "scope": "user:email",
    },
    "apple": {
        # Apple is more complex, usually requires specific library for Sign In with Apple
        # This is a placeholder for the OIDC flow
        "client_id": os.getenv("APPLE_CLIENT_ID", ""),
        "client_secret": os.getenv("APPLE_CLIENT_SECRET", ""),
        "auth_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "scope": "name email",
    },
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


class PullRequestRequest(BaseModel):
    title: str
    description: str
    source_branch: str
    target_branch: str
    repo_url: Optional[str] = ""


class PullRequestResponse(BaseModel):
    id: str
    title: str
    description: str
    source_branch: str
    target_branch: str
    author: str
    created_at: str
    status: str
    files: List[Dict[str, Any]]


class PRAnalysisRequest(BaseModel):
    pr_id: str
    gemini_key: Optional[str] = ""


class PRActionRequest(BaseModel):
    pr_id: str
    action: str  # 'approve', 'request_changes', 'merge'
    feedback: Optional[str] = ""


class CloneRequest(BaseModel):
    repo_url: str


class Token(BaseModel):
    access_token: str
    token_type: str


# --- 5. Helper Functions ---
def get_pr_analysis_prompt(pr_data: Dict[str, Any]) -> str:
    """Generate AI prompt for PR analysis with super-context"""
    files_info = []
    for file in pr_data.get("files", []):
        file_info = f"File: {file['path']} ({file['status']})\n"
        if file.get("original_content") and file.get("modified_content"):
            file_info += f"Changes:\n{file['original_content'][:500]}...\n→\n{file['modified_content'][:500]}...\n"
        files_info.append(file_info)

    prompt = f"""
Analyze this pull request with comprehensive context:

PR Details:
- Title: {pr_data.get('title', 'N/A')}
- Description: {pr_data.get('description', 'N/A')}
- Source Branch: {pr_data.get('source_branch', 'N/A')}
- Target Branch: {pr_data.get('target_branch', 'N/A')}
- Author: {pr_data.get('author', 'N/A')}

Files Changed:
{chr(10).join(files_info)}

Please provide:
1. **Summary**: Brief overview of changes and their purpose
2. **Potential Risks**: Security, performance, or compatibility issues
3. **Suggestions**: Improvements, best practices, or optimizations
4. **Confidence**: Your confidence level in this analysis (0-1)

Focus on code quality, security implications, and potential breaking changes.
Be thorough but concise in your analysis.
"""
    return prompt


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
        logger.error(f"GitHub Error: {context}")
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


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def _sign_oauth_state(state: str) -> str:
    signature = hmac.new(SECRET_KEY.encode(), state.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def _build_oauth_state() -> str:
    raw = secrets.token_urlsafe(32)
    signature = _sign_oauth_state(raw)
    return f"{raw}.{signature}"


def _verify_oauth_state(state: str) -> bool:
    try:
        raw, signature = state.rsplit(".", 1)
        expected = _sign_oauth_state(raw)
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False


def get_user_from_token(token: str, db: Session):
    """
    Decodes a JWT token and returns the corresponding user from the database.
    Returns None if token is invalid or user not found.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        logger.warning("Invalid JWT token provided.")
        return None

    user = db.query(User).filter(User.email == email).first()
    return user


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Extracts user from JWT in Authorization header.
    Returns None if no token or invalid, allowing guest access if desired.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    return get_user_from_token(token, db)


# --- 6. API Endpoints ---
@app.get("/")
async def health_check():
    return {"status": "ok", "service": "AI Chat Backend"}


# --- Auth Endpoints ---
@app.get("/auth/login/{provider}")
async def login(provider: str):
    if provider not in OAUTH_CONFIG:
        raise HTTPException(status_code=400, detail="Invalid provider")

    config = OAUTH_CONFIG[provider]
    if not config["client_id"]:
        logger.warning(f"{provider} Client ID not configured in environment variables.")
        return {
            "error": f"{provider} Client ID not configured in environment variables"
        }

    # Use environment variable for redirect_uri, fallback to localhost for dev
    redirect_uri = os.getenv(
        "OAUTH_REDIRECT_URI", f"http://localhost:8000/auth/callback/{provider}"
    )

    state = _build_oauth_state()
    params = {
        "client_id": config["client_id"],
        "response_type": "code",
        "scope": config["scope"],
        "redirect_uri": redirect_uri,
        "access_type": "offline",
        "state": state,
    }

    # Construct URL
    import urllib.parse

    url = f"{config['auth_url']}?{urllib.parse.urlencode(params)}"
    return {"url": url}


@app.get("/auth/callback/{provider}")
async def auth_callback(provider: str, code: str, state: str, db: Session = Depends(get_db)):
    if provider not in OAUTH_CONFIG:
        raise HTTPException(status_code=400, detail="Invalid provider")

    if not _verify_oauth_state(state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    config = OAUTH_CONFIG[provider]

    # Use environment variable for redirect_uri, fallback to localhost for dev
    redirect_uri = os.getenv(
        "OAUTH_REDIRECT_URI", f"http://localhost:8000/auth/callback/{provider}"
    )

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            config["token_url"],
            data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        token_data = token_res.json()
        access_token = token_data.get("access_token")

        if not access_token:
            logger.error(
                f"Failed to retrieve access token for {provider}: {token_data.get('error_description') or token_data.get('error')}"
            )
            raise HTTPException(
                status_code=400, detail="Failed to retrieve access token"
            )

        # Get User Info
        user_info_res = await client.get(
            config["user_info_url"], headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_info_res.json()

        # Normalize email/id based on provider
        email = user_data.get("email")
        provider_id = str(user_data.get("id") or user_data.get("sub"))

        if not email:
            # Fallback for GitHub if email is private or not provided by default user info endpoint
            # Attempt to fetch from /user/emails for GitHub
            if provider == "github":
                emails_res = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                emails_data = emails_res.json()
                primary_email = next(
                    (e["email"] for e in emails_data if e["primary"] and e["verified"]),
                    None,
                )
                if primary_email:
                    email = primary_email
                else:
                    logger.warning(
                        f"GitHub user {provider_id} has no public or primary verified email. Using placeholder."
                    )
                    email = f"{provider_id}@{provider}.placeholder.com"
            else:
                logger.warning(f"User from {provider} has no email. Using placeholder.")
                email = f"{provider_id}@{provider}.placeholder.com"

        # Save/Update User
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, provider=provider, provider_id=provider_id)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update existing user's provider_id if it changed (e.g., re-auth)
            user.provider_id = provider_id
            db.commit()
            db.refresh(user)

        # Create JWT
        jwt_token = create_access_token(data={"sub": user.email})

        # Use environment variable for frontend_url, fallback to localhost for dev
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{frontend_url}/login?token={jwt_token}")


@app.get("/api/processes")
async def list_processes():
    processes = []
    for proc in psutil.process_iter(
        ["pid", "name", "username", "cpu_percent", "memory_info"]
    ):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            logger.warning(f"Could not access process info for some process.")
            pass
    return processes


@app.post("/api/chat")
async def chat_endpoint(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

        # 5. Save to Database if user is logged in
        if current_user:
            # Save User Message
            user_msg = ChatMessage(
                user_id=current_user.id, sender="You", text=req.message
            )
            db.add(user_msg)

            # Save AI Response
            ai_msg = ChatMessage(
                user_id=current_user.id, sender=sender, text=response_text
            )
            db.add(ai_msg)

            db.commit()
            db.refresh(user_msg)  # Refresh to get generated timestamp
            db.refresh(ai_msg)  # Refresh to get generated timestamp

        return {
            "sender": sender,
            "text": response_text,
            "timestamp": datetime.now().strftime(
                "%H:%M"
            ),  # Use current time for API response
        }

    except Exception as e:
        logger.error(f"Error in chat_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fs/list")
async def list_files(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=401, detail="Authentication required to list files"
        )

    files = []

    # Determine user workspace
    target_dir = os.path.join(WORKSPACE_DIR, str(current_user.id))
    os.makedirs(target_dir, exist_ok=True)

    for root, dirs, filenames in os.walk(target_dir):
        # Exclude hidden directories and common build/env folders
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in ["node_modules", "__pycache__", "venv", "dist", "build"]
        ]

        rel_path = os.path.relpath(root, target_dir)
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
            # Exclude common temporary/config files
            if not f.startswith(".") and not f.endswith(("~", ".bak", ".tmp")):
                files.append(
                    {
                        "name": f,
                        "type": "file",
                        "path": os.path.join(rel_path, f).replace("\\", "/"),
                    }
                )
    return files


@app.post("/api/fs/read")
async def read_file(
    req: FileReadRequest, current_user: User = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=401, detail="Authentication required to read files"
        )

    base_dir = os.path.join(WORKSPACE_DIR, str(current_user.id))
    os.makedirs(base_dir, exist_ok=True)  # Ensure user's base dir exists

    safe_path = os.path.normpath(os.path.join(base_dir, req.path))

    # Security check: ensure path is within the user's workspace
    if not safe_path.startswith(base_dir):
        logger.warning(
            f"User {current_user.email} attempted to access file outside workspace: {req.path}"
        )
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        logger.error(
            f"Error reading file {req.path} for user {current_user.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fs/write")
async def write_file(
    req: FileWriteRequest, current_user: User = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=401, detail="Authentication required to write files"
        )

    base_dir = os.path.join(WORKSPACE_DIR, str(current_user.id))
    os.makedirs(base_dir, exist_ok=True)

    safe_path = os.path.normpath(os.path.join(base_dir, req.path))
    if not safe_path.startswith(base_dir):
        logger.warning(
            f"User {current_user.email} attempted to write file outside workspace: {req.path}"
        )
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {"status": "ok"}
    except Exception as e:
        logger.error(
            f"Error writing file {req.path} for user {current_user.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tool")
async def run_tool(req: ToolRequest, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=401, detail="Authentication required to use AI tools"
        )

    # Create a temporary client using the key provided in request (or default)
    client = get_ai_client(ChatRequest(message="", gemini_key=req.gemini_key))
    prompt = get_tool_prompt(req.tool, req.code)
    result = client.ask_gemini(prompt)
    return {"result": result}


@app.post("/api/git/clone")
async def clone_repo(req: CloneRequest, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=401, detail="Authentication required to clone repositories"
        )

    try:
        base_dir = os.path.join(WORKSPACE_DIR, str(current_user.id))
        os.makedirs(base_dir, exist_ok=True)

        # Extract repo name
        repo_name = req.repo_url.split("/")[-1].replace(".git", "")
        target_dir = os.path.join(base_dir, repo_name)

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
            logger.error(
                f"Git clone failed for user {current_user.email}, repo {req.repo_url}: {process.stderr}"
            )
            raise Exception(f"Git clone failed: {process.stderr}")

        return {"status": "ok", "message": f"Cloned '{repo_name}' successfully."}
    except Exception as e:
        logger.error(
            f"Error cloning repo {req.repo_url} for user {current_user.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fs/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=401, detail="Authentication required to upload files"
        )

    try:
        base_dir = os.path.join(WORKSPACE_DIR, str(current_user.id))
        os.makedirs(base_dir, exist_ok=True)

        file_path = os.path.join(base_dir, file.filename)

        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # If zip, extract it
        if file.filename.endswith(".zip"):
            extract_dir = os.path.join(base_dir, os.path.splitext(file.filename)[0])
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            os.remove(file_path)  # Always remove zip after extraction for cleanliness
            message = f"Uploaded and extracted '{file.filename}'."
        else:
            message = f"Uploaded '{file.filename}'."

        # Save metadata to DB
        db_file = FileRecord(
            user_id=current_user.id, filename=file.filename, file_path=file_path
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        return {"status": "ok", "message": message}
    except Exception as e:
        logger.error(
            f"Error uploading file {file.filename} for user {current_user.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


# --- Pull Request Endpoints ---
@app.get("/api/pr/list")
async def list_pull_requests(current_user: User = Depends(get_current_user)):
    """List all pull requests for the user"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # For now, return empty list - in a real implementation, this would query a database
    return {"pull_requests": []}


@app.post("/api/pr/create")
async def create_pull_request(
    req: PullRequestRequest, current_user: User = Depends(get_current_user)
):
    """Create a new pull request"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Generate a unique PR ID
        pr_id = f"pr_{int(time.time())}_{current_user.id}"

        # In a real implementation, this would:
        # 1. Parse git diff between branches
        # 2. Extract file changes
        # 3. Store PR in database

        pr_data = {
            "id": pr_id,
            "title": req.title,
            "description": req.description,
            "source_branch": req.source_branch,
            "target_branch": req.target_branch,
            "author": current_user.email,
            "created_at": datetime.now().isoformat(),
            "status": "open",
            "files": [],  # Would contain actual file changes
        }

        return {"pull_request": pr_data}

    except Exception as e:
        logger.error(f"Error creating pull request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pr/{pr_id}")
async def get_pull_request(pr_id: str, current_user: User = Depends(get_current_user)):
    """Get details of a specific pull request"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # For now, return a mock PR - in a real implementation, this would query database
    mock_pr = {
        "id": pr_id,
        "title": "Sample Pull Request",
        "description": "This is a sample pull request for testing purposes.",
        "source_branch": "feature-branch",
        "target_branch": "main",
        "author": current_user.email,
        "created_at": datetime.now().isoformat(),
        "status": "open",
        "files": [
            {
                "path": "src/example.js",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "original_content": "// Original code\nfunction oldFunction() {\n  return 'old';\n}",
                "modified_content": "// Modified code\nfunction newFunction() {\n  return 'new';\n}",
            }
        ],
    }

    return {"pull_request": mock_pr}


@app.post("/api/pr/{pr_id}/analyze")
async def analyze_pull_request(
    pr_id: str, req: PRAnalysisRequest, current_user: User = Depends(get_current_user)
):
    """Analyze a pull request using AI"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Get PR data (in real implementation, this would come from database)
        pr_data = {
            "id": pr_id,
            "title": "Sample Pull Request",
            "description": "This is a sample pull request for testing purposes.",
            "source_branch": "feature-branch",
            "target_branch": "main",
            "author": current_user.email,
            "files": [
                {
                    "path": "src/example.js",
                    "status": "modified",
                    "original_content": "// Original code\nfunction oldFunction() {\n  return 'old';\n}",
                    "modified_content": "// Modified code\nfunction newFunction() {\n  return 'new';\n}",
                }
            ],
        }

        # Create AI client
        client = get_ai_client(ChatRequest(message="", gemini_key=req.gemini_key))

        # Generate analysis prompt
        prompt = get_pr_analysis_prompt(pr_data)

        # Get AI analysis
        analysis_text = client.ask_gemini(prompt)

        # Parse AI response (in a real implementation, this would be more sophisticated)
        ai_analysis = {
            "summary": "AI analysis completed for this pull request.",
            "risks": ["Potential breaking changes detected", "Consider adding tests"],
            "suggestions": ["Add error handling", "Update documentation"],
            "confidence": 0.85,
        }

        return {"analysis": ai_analysis}

    except Exception as e:
        logger.error(f"Error analyzing pull request {pr_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pr/{pr_id}/action")
async def pull_request_action(
    pr_id: str, req: PRActionRequest, current_user: User = Depends(get_current_user)
):
    """Perform an action on a pull request (approve, request changes, merge)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # In a real implementation, this would:
        # 1. Validate the action
        # 2. Update PR status in database
        # 3. Send notifications
        # 4. Execute git operations for merge

        if req.action == "approve":
            return {"message": f"Pull request {pr_id} approved"}
        elif req.action == "request_changes":
            return {"message": f"Changes requested for pull request {pr_id}"}
        elif req.action == "merge":
            return {"message": f"Pull request {pr_id} merged"}
        else:
            raise HTTPException(status_code=400, detail="Invalid action")

    except Exception as e:
        logger.error(
            f"Error performing action {req.action} on PR {pr_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


# --- Terminal Endpoint (WebSocket) ---
@app.websocket("/ws/terminal")
async def terminal_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    user = get_user_from_token(token, db)
    if not user:
        logger.warning("WebSocket connection attempt with invalid token.")
        await websocket.close(code=1008, reason="Authentication failed")
        return

    logger.info(f"WebSocket connection accepted for user: {user.email}")
    await websocket.accept()

    # Determine user's workspace for terminal
    user_workspace_dir = os.path.join(WORKSPACE_DIR, str(user.id))
    os.makedirs(user_workspace_dir, exist_ok=True)  # Ensure user's workspace exists

    # Check for PTY support (Linux/macOS only)
    try:
        import pty

        use_pty = True
    except ImportError:
        use_pty = False
        logger.warning(
            "PTY module not available. Falling back to Windows subprocess or limited shell."
        )

    if use_pty:
        # Spawn Shell with TERM environment variable for colors
        master_fd, slave_fd = pty.openpty()
        shell = os.environ.get("SHELL", "/bin/bash")

        # Important: Set TERM so tools know to output color
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["PWD"] = user_workspace_dir  # Set initial working directory
        env["HOME"] = user_workspace_dir  # Set HOME for user-specific configs

        process = subprocess.Popen(
            [shell],
            preexec_fn=os.setsid,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            universal_newlines=True,
            env=env,
            cwd=user_workspace_dir,  # Set current working directory for the shell
        )

        os.close(slave_fd)  # Close slave in parent

        loop = asyncio.get_running_loop()

        async def send_output():
            try:
                # Read from PTY and send to WebSocket
                output = await loop.run_in_executor(
                    None, lambda: os.read(master_fd, 10240)
                )
                if output:
                    await websocket.send_text(output.decode(errors="ignore"))
                else:
                    # EOF - process exited
                    logger.info(f"Terminal process for user {user.email} exited.")
                    await websocket.close()
            except Exception as e:
                logger.error(
                    f"Error reading from PTY for user {user.email}: {e}", exc_info=True
                )
                await websocket.close(code=1011, reason="Internal server error")

        # Register reader for PTY output
        loop.add_reader(master_fd, lambda: asyncio.create_task(send_output()))

        try:
            while True:
                # Receive from WebSocket and write to PTY
                data = await websocket.receive_text()
                os.write(master_fd, data.encode())
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user.email}.")
        except Exception as e:
            logger.error(f"Terminal error for user {user.email}: {e}", exc_info=True)
        finally:
            loop.remove_reader(master_fd)
            process.kill()
            os.close(master_fd)
    else:  # Windows fallback or PTY not available
        if os.name == "nt":
            try:
                shell = os.environ.get("COMSPEC", "cmd.exe")
                process = await asyncio.create_subprocess_shell(
                    shell,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=user_workspace_dir,  # Set current working directory for the shell
                )

                async def read_stream(stream, stream_name):
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
                    except Exception as e:
                        logger.error(
                            f"Error reading from {stream_name} stream for user {user.email}: {e}",
                            exc_info=True,
                        )
                        pass  # Don't close websocket on stream error, let main loop handle it

                asyncio.create_task(read_stream(process.stdout, "stdout"))
                asyncio.create_task(read_stream(process.stderr, "stderr"))

                try:
                    while True:
                        data = await websocket.receive_text()
                        process.stdin.write(data.encode())
                        await process.stdin.drain()
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for user {user.email}.")
                except Exception as e:
                    logger.error(
                        f"Terminal error for user {user.email}: {e}", exc_info=True
                    )
                finally:
                    try:
                        process.terminate()
                    except:
                        pass
                return
            except Exception as e:
                logger.error(
                    f"Error starting Windows terminal for user {user.email}: {e}",
                    exc_info=True,
                )
                await websocket.send_text(f"Error starting Windows terminal: {e}\r\n")
                await websocket.close(code=1011, reason="Internal server error")
                return
        else:
            logger.error(
                "Backend terminal requires Linux/macOS (pty module missing) or Windows (cmd.exe)."
            )
            await websocket.send_text(
                "Error: Backend terminal requires Linux/macOS (pty module missing) or Windows (cmd.exe).\r\n"
            )
            await websocket.close(code=1011, reason="Internal server error")
            return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
