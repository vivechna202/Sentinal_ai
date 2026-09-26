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

def _run_automated_tests(path: str, verify_command: str = None) -> str:
    """Helper function to run automated syntax checks and tests after a file edit."""
    feedback = ""
    # 1. Automatic Syntax Checking
    if path.endswith(".py"):
        try:
            result = subprocess.run(
                f'python -m py_compile \"{path}\"', 
                shell=True, capture_output=True, text=True
            )
            if result.returncode != 0:
                feedback += f"\n\n🚨 SYNTAX ERROR DETECTED IN {path} 🚨\n{result.stderr.strip()}\nYou must fix this syntax error!"
            else:
                feedback += f"\n\n✅ Automatic Python syntax check passed for {path}."
        except Exception:
            pass

    # 2. Integrated Test Runner
    if verify_command:
        try:
            feedback += f"\n\n▶️ Running verification command: `{verify_command}`\n"
            result = subprocess.run(
                verify_command, 
                shell=True, capture_output=True, text=True, timeout=60
            )
            output = result.stdout
            if result.stderr:
                output += "\nSTDERR:\n" + result.stderr
            
            output = output.strip() if output.strip() else "Command executed successfully with no output."
            if result.returncode != 0:
                feedback += f"❌ TEST FAILED (Exit code {result.returncode})! Analyze this output and fix your code:\n\n{output}"
            else:
                feedback += f"✅ TEST PASSED:\n\n{output}"
        except Exception as e:
            feedback += f"❌ Error running verification command: {str(e)}"
            
    # Auto-checkpointing has been removed as per user request.
    
    return feedback


def create_file(path: str, content: str, verify_command: str = None) -> str:
    """Creates a BRAND NEW file with the given content.
    Do NOT use this to edit existing files.
    
    Args:
        path: The path to the new file.
        content: The initial text content.
        verify_command: Optional terminal command to run tests/linters immediately after creation.
        
    Returns:
        A success message combined with automated test results.
    """
    try:
        if os.path.exists(path):
            return "Error: File already exists. You MUST use edit_file to modify existing files."
            
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        response = f"Successfully created {path}."
        response += _run_automated_tests(path, verify_command)
        return response
    except Exception as e:
        return f"Error creating file: {str(e)}"

def edit_file(path: str, target_text: str, replacement_text: str, verify_command: str = None) -> str:
    """Edits an existing file by replacing a specific block of text.
    Use this for precise edits rather than full-file rewrites.
    
    Args:
        path: The path to the file to edit.
        target_text: The EXACT text block in the file you want to replace.
        replacement_text: The text you want to insert in its place.
        verify_command: Optional terminal command to run tests/linters immediately after editing.
        
    Returns:
        A success message combined with automated test results.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if target_text not in content:
            return "Error: target_text not found in the file. Read the file again to get the exact string."
            
        new_content = content.replace(target_text, replacement_text, 1)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        response = f"Successfully edited {path}."
        response += _run_automated_tests(path, verify_command)
        return response
    except Exception as e:
        return f"Error editing file: {str(e)}"

def run_verification(command: str) -> str:
    """Runs a terminal command to verify your recent edits. 
    You MUST call this immediately after editing a file.
    
    Args:
        command: The test or lint command to run (e.g., 'pytest', 'node script.js').
        
    Returns:
        The output of the test. If it fails, you must observe the errors and fix them.
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
            
        final_output = output.strip() if output.strip() else "Command executed successfully with no output."
        if result.returncode != 0:
            return f"TEST FAILED (Exit code {result.returncode})! Analyze this output and fix your code:\n\n{final_output}"
        return f"TEST PASSED:\n\n{final_output}"
    except Exception as e:
        return f"Error verifying: {str(e)}"
def list_directory(path: str) -> str:
    """Lists all files and folders in a given directory to help navigate the codebase.
    
    Args:
        path: The path to the directory (use '.' for the current workspace).
        
    Returns:
        A string containing the folder structure, ignoring common hidden folders.
    """
    try:
        import os
        ignored_dirs = {'.git', '.venv', '__pycache__', 'node_modules', '.chainlit', '.streamlit', '.files'}
        result = []
        
        if not os.path.isdir(path):
            return f"Error: {path} is not a valid directory."
            
        for root, dirs, files in os.walk(path):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            level = root.replace(path, '').count(os.sep)
            indent = ' ' * 4 * level
            result.append(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                result.append(f"{subindent}{f}")
                
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def grep_search(query: str, directory: str = ".") -> str:
    """Searches for a specific keyword or function name across all text files in a directory.
    Use this to find where variables or functions are defined or used.
    
    Args:
        query: The string to search for.
        directory: The folder to search inside (defaults to current folder '.').
        
    Returns:
        A list of file paths and line numbers matching the query.
    """
    import os
    ignored_dirs = {'.git', '.venv', '__pycache__', 'node_modules'}
    results = []
    
    try:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                # Basic check to skip likely binary files
                if file.endswith(('.exe', '.dll', '.zip', '.png', '.jpg', '.lock', '.pyc')):
                    continue
                    
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if query in line:
                                results.append(f"{filepath}:{line_num}: {line.strip()}")
                                if len(results) >= 50:
                                    return "\n".join(results) + "\n\n... (capped at 50 results. Please narrow your search.)"
                except Exception:
                    pass # Skip unreadable files
                    
        if not results:
            return f"No results found for '{query}'"
        return "\n".join(results)
    except Exception as e:
        return f"Error searching: {str(e)}"

def git_checkpoint(message: str) -> str:
    """Creates a Git commit to save the current state of the code safely.
    Call this BEFORE making risky edits or large refactors!
    
    Args:
        message: A brief description of the current working state.
        
    Returns:
        Success or failure message.
    """
    try:
        # Check if git is initialized
        if not os.path.exists(".git"):
            subprocess.run("git init", shell=True, capture_output=True)
            
        subprocess.run("git add .", shell=True, capture_output=True)
        result = subprocess.run(f'git commit -m "Agent Checkpoint: {message}"', shell=True, capture_output=True, text=True)
        return "Checkpoint saved! You can now safely edit. If you break it, use git_rollback."
    except Exception as e:
        return f"Error saving checkpoint: {str(e)}"

def git_rollback() -> str:
    """Reverts the entire codebase back to the last git_checkpoint.
    Use this if your tests are failing repeatedly and you need a clean slate to try a different approach.
    
    Returns:
        Success or failure message.
    """
    try:
        result = subprocess.run("git reset --hard HEAD", shell=True, capture_output=True, text=True)
        subprocess.run("git clean -fd", shell=True, capture_output=True) # Removes untracked files too
        return "Codebase successfully rolled back to the last checkpoint! You have a clean slate."
    except Exception as e:
        return f"Error rolling back: {str(e)}"
def execute_command(command: str, approved: bool = False) -> str:
    """Executes a shell command on the host system.
    WARNING: For any dangerous command (e.g. rm, git push, pip install, etc), you MUST ask the user for permission in the chat first!
    Once they say yes, call this tool again with approved=True.
    
    Args:
        command: The shell command to run.
        approved: Set to True ONLY if the user explicitly told you to run this in the chat.
        
    Returns:
        The standard output or error of the command, OR a rejection message if not approved.
    """
    # Safety Whitelist for Read-Only or Test Commands
    safe_prefixes = ('ls', 'dir', 'echo', 'cat', 'grep', 'find', 'pytest', 'python --version', 'git status', 'git log')
    
    is_safe = any(command.strip().startswith(prefix) for prefix in safe_prefixes)
    
    if not is_safe and not approved:
        return (
            "❌ ACTION BLOCKED: This command might modify the system or run arbitrary code. "
            f"You are trying to run: `{command}`\n"
            "You MUST output a message to the user asking for permission. "
            "Wait for them to reply 'yes' or 'approved'. "
            "Then, call this tool again with `approved=True`."
        )

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
AGENT_TOOLS = [read_file, create_file, edit_file, run_verification, list_directory, grep_search, git_checkpoint, git_rollback, execute_command, search_web, run_python_code]
