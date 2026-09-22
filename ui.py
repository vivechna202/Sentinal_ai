import os
import sys
import asyncio

# Hack to suppress noisy asyncio ConnectionResetError on Windows when stopping generation
if sys.platform == "win32":
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        def silence_connection_lost(func):
            def wrapper(self, exc=None):
                try:
                    func(self, exc)
                except ConnectionResetError:
                    pass
            return wrapper
        _ProactorBasePipeTransport._call_connection_lost = silence_connection_lost(_ProactorBasePipeTransport._call_connection_lost)
    except Exception:
        pass
import streamlit as st
from google import genai
from google.genai import types
from tools import AGENT_TOOLS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Coding Agent", page_icon="🤖", layout="wide")

# Cloud Awareness Logic
is_cloud = os.environ.get("RUNNING_IN_CLOUD") == "True"

if is_cloud:
    st.sidebar.title("☁️ Cloud Demo Mode")
    st.sidebar.warning("You are using the web demo. For security, local file access and terminal execution are disabled.")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Run Sentinel AI Locally!")
    st.sidebar.markdown("Unlock full capabilities by running it on your own PC.")
    
    # Read the install.bat file to serve as a download
    try:
        with open("install.bat", "rb") as f:
            bat_content = f.read()
        st.sidebar.download_button(
            label="⬇️ Download Local Installer (.bat)",
            data=bat_content,
            file_name="install_sentinel_ai.bat",
            mime="application/x-msdownload"
        )
    except FileNotFoundError:
        st.sidebar.error("Installer script missing.")
        
    # Restrict tools in cloud mode (only allow web search)
    from tools import search_web
    active_tools = [search_web]
    welcome_text = "Welcome to the Cloud Demo! I can 🌐 **Search the Web** and chat, but local tools are disabled. Download the installer to unlock my full potential!"
else:
    active_tools = AGENT_TOOLS
    welcome_text = "Welcome! I am equipped with tools for: 📁 **File IO**, 💻 **Terminal**, 🌐 **Web Search**, and 🐍 **Python Execution**."

st.title("🤖 Custom Coding Agent")
st.markdown(welcome_text)

# Initialize session state for messages and the Gemini chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "chat" not in st.session_state:
    if not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") == "your_api_key_here":
        st.error("❌ Error: `GEMINI_API_KEY` is not set correctly in your `.env` file. Please update it and restart.")
        st.stop()
        
    client = genai.Client()
    system_instruction = (
        "You are an expert coding agent running on the user's local machine. "
        "You have access to tools to help the user. If you are in cloud mode, you only have web search. "
        "Always explain what you are doing."
    )
    
    st.session_state.chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            tools=active_tools,
            system_instruction=system_instruction,
            temperature=0.4,
        )
    )

# Render existing messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input block
if prompt := st.chat_input("How can I help you build today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    with st.chat_message("assistant"):
        with st.spinner("Thinking and working..."):
            try:
                # send_message is blocking and natively supported in Streamlit!
                response = st.session_state.chat.send_message(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
