import os
import json
import threading
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

# Global state for a single-user local app
genai_client = None
chat_session = None
chat_history = []
stop_event = threading.Event()

class PromptRequest(BaseModel):
    prompt: str

def initialize_chat():
    global genai_client, chat_session, chat_history
    if not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") == "your_api_key_here":
        print("Error: GEMINI_API_KEY not set in .env")
        return False
        
    genai_client = genai.Client()
    system_instruction = (
        "You are an autonomous Software Engineering (SWE) agent. "
        "You MUST strictly follow this loop: READ/SEARCH the code -> EDIT the code using targeted replacements -> "
        "TEST the code immediately using run_verification -> OBSERVE the output and repeat if necessary.\n"
        "Guidelines:\n"
        "1. Never declare a task complete until verification tests pass.\n"
        "2. Use grep_search and list_directory to navigate the codebase instead of guessing file paths.\n"
        "3. Use git_checkpoint before making large or risky edits. If you get stuck in a loop of failing tests, use git_rollback to undo and try a different approach.\n"
        "If you are in cloud mode, you only have web search."
    )
    
    is_cloud = os.environ.get("RUNNING_IN_CLOUD") == "True"
    
    # Filter tools if in cloud mode
    if is_cloud:
        active_tools = [t for t in AGENT_TOOLS if t.__name__ == "search_web"]
    else:
        active_tools = AGENT_TOOLS
        
    chat_session = genai_client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            tools=active_tools,
            system_instruction=system_instruction,
            temperature=0.4,
        )
    )
    chat_history = [{"role": "assistant", "content": "Hello! I am your SWE-agent. How can I help you build today?"}]
    return True

@app.get("/")
async def index(request: Request):
    if chat_session is None:
        if not initialize_chat():
            return JSONResponse(
                status_code=500, 
                content={"error": "Please configure your GEMINI_API_KEY in the .env file."}
            )
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/history")
async def history():
    return {"messages": chat_history}

@app.post("/chat")
async def chat(request: PromptRequest):
    if chat_session is None:
        if not initialize_chat():
            return JSONResponse(status_code=500, content={"error": "Failed to initialize chat. Check API Key."})
            
    prompt = request.prompt
    if not prompt:
        return JSONResponse(status_code=400, content={"error": "No prompt provided"})
        
    chat_history.append({"role": "user", "content": prompt})
    stop_event.clear()
    
    def generate():
        full_response = ""
        try:
            # send_message_stream is a synchronous generator. 
            # FastAPI runs this generator in a background threadpool so it doesn't block the async loop!
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
        
        # Signal the end of the stream
        yield "data: [DONE]\n\n"
        chat_history.append({"role": "assistant", "content": full_response})

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/stop")
async def stop():
    stop_event.set()
    return {"status": "stopped"}
