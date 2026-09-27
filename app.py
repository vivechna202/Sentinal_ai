import os
import json
import threading
import uuid
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from google import genai
from google.genai import types
from tools import AGENT_TOOLS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Sentinel AI SWE-Agent")

# Configure templates directory
templates = Jinja2Templates(directory="templates")

# Configure database directory
CHATS_DIR = "chats"
os.makedirs(CHATS_DIR, exist_ok=True)
CHATS_FILE = os.path.join(CHATS_DIR, "chats.json")

genai_client = None
active_sessions = {}  # session_id -> google-genai chat_session object
stop_event = threading.Event()

class PromptRequest(BaseModel):
    prompt: str
    session_id: str

def load_chats_db():
    if os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_chats_db(db):
    with open(CHATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4)

def get_config():
    system_instruction = (
        "You are an autonomous Software Engineering (SWE) agent. "
        "You MUST strictly follow this loop: READ/SEARCH the code -> EDIT the code using targeted replacements -> "
        "TEST the code immediately using run_verification -> OBSERVE the output and repeat if necessary.\n"
        "Guidelines:\n"
        "1. Never declare a task complete until verification tests pass.\n"
        "2. Use grep_search and list_directory to navigate the codebase instead of guessing file paths.\n"
        "3. Use git_checkpoint before making large or risky edits. If you get stuck in a loop of failing tests, use git_rollback to undo and try a different approach.\n"
        "4. YOU HAVE FULL ABILITY to run terminal commands (like pip install) using execute_command, and to create/edit files. DO NOT tell the user you cannot do these things.\n"
        "5. If a tool returns 'ACTION BLOCKED', it means the safety gate caught it. Simply output a chat message asking the user for permission. Once they reply 'yes', call the exact same tool again but with `approved=True`.\n"
        "If you are in cloud mode, you only have web search."
    )
    is_cloud = os.environ.get("RUNNING_IN_CLOUD") == "True"
    active_tools = [t for t in AGENT_TOOLS if t.__name__ == "search_web"] if is_cloud else AGENT_TOOLS
    return types.GenerateContentConfig(tools=active_tools, system_instruction=system_instruction, temperature=0.4)

def init_client():
    global genai_client
    if not genai_client:
        if not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") == "your_api_key_here":
            return False
        genai_client = genai.Client()
    return True

def get_or_create_session(session_id: str):
    global genai_client, active_sessions
    if not init_client(): return None
    
    if session_id in active_sessions:
        return active_sessions[session_id]
        
    db = load_chats_db()
    if session_id not in db:
        return None # Invalid session
        
    # Reconstruct gemini history
    gemini_history = []
    for msg in db[session_id]["history"]:
        if msg["content"].startswith("Hello! I am your SWE-agent"): continue
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(msg["content"])]))
        
    chat = genai_client.chats.create(
        model="gemini-2.5-flash",
        config=get_config(),
        history=gemini_history if gemini_history else None
    )
    active_sessions[session_id] = chat
    return chat

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/sessions")
async def get_sessions():
    db = load_chats_db()
    sessions = []
    for sid, data in db.items():
        sessions.append({"id": sid, "title": data["title"], "updated_at": data["updated_at"]})
    # Sort by updated_at descending
    sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"sessions": sessions}

@app.post("/sessions")
async def create_session():
    db = load_chats_db()
    session_id = str(uuid.uuid4())
    db[session_id] = {
        "title": "New Chat",
        "updated_at": datetime.now().isoformat(),
        "history": [{"role": "assistant", "content": "Hello! I am your SWE-agent. How can I help you build today?"}]
    }
    save_chats_db(db)
    return {"id": session_id}

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    db = load_chats_db()
    if session_id in db:
        return {"messages": db[session_id]["history"]}
    return JSONResponse(status_code=404, content={"error": "Session not found"})

@app.post("/chat")
async def chat(request: PromptRequest):
    session_id = request.session_id
    prompt = request.prompt
    
    if not prompt:
        return JSONResponse(status_code=400, content={"error": "No prompt provided"})
        
    chat_session = get_or_create_session(session_id)
    if not chat_session:
        return JSONResponse(status_code=500, content={"error": "Failed to load chat. Check API Key."})
        
    db = load_chats_db()
    db[session_id]["history"].append({"role": "user", "content": prompt})
    
    # Auto-generate title if it's the first user message
    if len(db[session_id]["history"]) == 2:
        db[session_id]["title"] = prompt[:30] + ("..." if len(prompt) > 30 else "")
        
    db[session_id]["updated_at"] = datetime.now().isoformat()
    save_chats_db(db)
    
    stop_event.clear()
    
    def generate():
        full_response = ""
        try:
            for chunk in chat_session.send_message_stream(prompt):
                if stop_event.is_set():
                    yield "data: [STOPPED BY USER]\n\n"
                    full_response += "\n\n*[Stopped by user]*"
                    break
                if chunk.text:
                    full_response += chunk.text
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        yield "data: [DONE]\n\n"
        
        # Save assistant response to DB
        db = load_chats_db()
        db[session_id]["history"].append({"role": "assistant", "content": full_response})
        db[session_id]["updated_at"] = datetime.now().isoformat()
        save_chats_db(db)

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/stop")
async def stop():
    stop_event.set()
    return {"status": "stopped"}
