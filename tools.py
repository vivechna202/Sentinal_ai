import os
import subprocess
from duckduckgo_search import DDGS

def read_file(path: str) -> str:
    """Reads the contents of a file at the given path.
    
    Args:
        path: The absolute or relative path to the file.
        
    Returns:
        The string contents of the file, or an error message if the file doesn't exist.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(path: str, content: str) -> str:
    """Writes the given content to a file, overwriting it if it exists.
    
    Args:
        path: The absolute or relative path to the file.
        content: The text content to write to the file.
        
    Returns:
        A success or error message.
    """
    try:
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def execute_command(command: str) -> str:
    """Executes a shell command on the host system.
    
    Args:
        command: The shell command to run.
        
    Returns:
        The standard output or error of the command.
    """
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        output = result.stdout
        if result.stderr:
            output += "\nSTDERR:\n" + result.stderr
        return output.strip() if output.strip() else "Command executed successfully with no output."
    except Exception as e:
        return f"Error executing command: {str(e)}"

def search_web(query: str) -> str:
    """Searches the web using DuckDuckGo for the given query.
    
    Args:
        query: The search query string.
        
    Returns:
        A formatted string containing the top search results.
    """
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No results found."
        
        formatted_results = []
        for r in results:
            formatted_results.append(f"Title: {r['title']}\nSnippet: {r['body']}\nLink: {r['href']}")
        
        return "\n\n---\n\n".join(formatted_results)
    except Exception as e:
        return f"Error searching the web: {str(e)}"

def run_python_code(code: str) -> str:
    """Executes a snippet of Python code and returns the printed output.
    
    Args:
        code: The Python code to execute.
        
    Returns:
        The output printed by the code or error traceback.
    """
    import sys
    import io
    import traceback
    
    # Create a string buffer to capture stdout
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    try:
        # Execute the code in a new dictionary to avoid polluting globals
        exec(code, {})
        output = redirected_output.getvalue()
        return output if output else "Code executed successfully with no printed output."
    except Exception as e:
        return traceback.format_exc()
    finally:
        sys.stdout = old_stdout

# List of all tools to be passed to the agent
AGENT_TOOLS = [read_file, write_file, execute_command, search_web, run_python_code]
