import os
import sys
from google import genai
from google.genai import types
from tools import AGENT_TOOLS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    print("🤖 Welcome to the Custom Coding Agent!")
    
    # Check for API Key
    if not os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") == "your_api_key_here":
        print("Error: GEMINI_API_KEY is not set correctly in your .env file.")
        print("Please open the .env file and replace 'your_api_key_here' with your actual API key.")
        sys.exit(1)
        
    # Initialize the client (automatically uses GEMINI_API_KEY from environment)
    client = genai.Client()
    
    # We use gemini-2.5-flash as it has a much more generous free tier
    model_name = "gemini-2.5-flash"
    
    system_instruction = (
        "You are an expert coding agent running on the user's local machine. "
        "You have access to tools to read/write files, execute terminal commands, "
        "search the web, and run Python code. Use these tools to accomplish the user's tasks. "
        "Always explain what you are doing. If a task requires multiple steps, use the tools "
        "one by one to gather information, make changes, and verify them."
    )
    
    # Create a chat session. The SDK will automatically handle calling the Python functions
    # provided in the `tools` list when the model requests them.
    chat = client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            tools=AGENT_TOOLS,
            system_instruction=system_instruction,
            temperature=0.4,
        )
    )
    
    print(f"Agent initialized with {len(AGENT_TOOLS)} tools.")
    print("Type 'exit' or 'quit' to stop.\n")
    
    # Interaction loop
    while True:
        try:
            user_input = input("You: ")
            if not user_input.strip():
                continue
                
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            print("\nAgent is thinking and working (this might take a moment if it uses tools)...\n")
            
            # send_message automatically handles the back-and-forth tool calling loop!
            response = chat.send_message(user_input)
            print(f"🤖 Agent: {response.text}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {e}\n")

if __name__ == "__main__":
    main()
