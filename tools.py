import os
import subprocess
import json
import uuid
from datetime import datetime
from duckduckgo_search import DDGS

class TaskState:
    def __init__(self):
        self.file_path = "tasks/current_task.json"
        os.makedirs("tasks", exist_ok=True)
        self.load()

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except:
                self.reset()
        else:
            self.reset()

    def reset(self, goal=""):
        self.data = {
            "task_id": str(uuid.uuid4()),
            "original_goal": goal,
            "current_plan": None,
            "current_step": "Planning",
            "files_inspected": [],
            "files_modified": [],
            "tools_executed": [],
            "verification_results": [],
            "errors_encountered": [],
            "recovery_attempts": [],
            "status": "in_progress",
            "completion_state": "incomplete",
            "updated_at": datetime.now().isoformat()
        }
        self.save()

    def save(self):
        self.data["updated_at"] = datetime.now().isoformat()
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def log_tool(self, tool_name):
        self.data["tools_executed"].append(tool_name)
        self.save()

    def log_file_inspected(self, path):
        if path not in self.data["files_inspected"]:
            self.data["files_inspected"].append(path)
        self.save()

    def log_file_modified(self, path):
        if path not in self.data["files_modified"]:
            self.data["files_modified"].append(path)
        self.save()

    def log_verification(self, result):
        self.data["verification_results"].append(result)
        if "❌" in result or "ERROR" in result:
            self.data["errors_encountered"].append(result)
        self.save()

    def log_error(self, error):
        self.data["errors_encountered"].append(error)
        self.save()
        
    def log_recovery_attempt(self, action: str):
        self.data["recovery_attempts"].append({
            "timestamp": datetime.now().isoformat(),
            "action": action
        })
        self.save()
        
    def check_recovery_limit(self, action: str, limit: int = 3) -> bool:
        count = 0
        for a in self.data.get("recovery_attempts", []):
            if isinstance(a, dict) and a.get("action") == action:
                count += 1
        return count >= limit

task_state = TaskState()

def read_file(path: str) -> str:
    """Reads the contents of a file at the given path."""
    task_state.log_tool("read_file")
    task_state.log_file_inspected(path)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        task_state.log_error(f"read_file error: {str(e)}")
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
                action = f"Syntax Error: {path}"
                task_state.log_recovery_attempt(action)
                if task_state.check_recovery_limit(action, limit=3):
                    feedback += f"\n\n🚨 SYNTAX ERROR DETECTED IN {path} 🚨\n{result.stderr.strip()}\n\n❌ MAXIMUM RECOVERY ATTEMPTS EXCEEDED (3). Stop editing this file automatically. You MUST output a message to the user asking for human intervention."
                else:
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
                action = f"Verify Failed: {verify_command}"
                task_state.log_recovery_attempt(action)
                if task_state.check_recovery_limit(action, limit=3):
                    feedback += f"❌ TEST FAILED (Exit code {result.returncode})!\n\n{output}\n\n❌ MAXIMUM RECOVERY ATTEMPTS EXCEEDED (3). Stop running this test automatically. Ask the user for help."
                else:
                    feedback += f"❌ TEST FAILED (Exit code {result.returncode})! Analyze this output and fix your code:\n\n{output}"
            else:
                feedback += f"✅ TEST PASSED:\n\n{output}"
        except Exception as e:
            feedback += f"❌ Error running verification command: {str(e)}"
            
    if feedback:
        task_state.log_verification(feedback)
    
    return feedback


def create_file(path: str, content: str, verify_command: str = None, approved: bool = False) -> str:
    """Creates a BRAND NEW file with the given content."""
    task_state.log_tool("create_file")
    if not approved:
        return (
            "❌ ACTION BLOCKED: You MUST output a message to the user asking for permission to create this file. "
            f"File: {path}\n"
            "Wait for them to reply 'yes' or 'approved'. "
            "Then, call this tool again with `approved=True`."
        )

    try:
        if os.path.exists(path):
            task_state.log_error(f"create_file error: File already exists at {path}")
            return "Error: File already exists. You MUST use edit_file to modify existing files."
            
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        task_state.log_file_modified(path)
        response = f"Successfully created {path}."
        response += _run_automated_tests(path, verify_command)
        return response
    except Exception as e:
        task_state.log_error(f"create_file error: {str(e)}")
        return f"Error creating file: {str(e)}"

def edit_file(path: str, target_text: str, replacement_text: str, verify_command: str = None, approved: bool = False) -> str:
    """Edits an existing file by replacing a specific block of text."""
    task_state.log_tool("edit_file")
    if not approved:
        return (
            "❌ ACTION BLOCKED: You MUST output a message to the user asking for permission to edit this file. "
            f"File: {path}\n"
            "Wait for them to reply 'yes' or 'approved'. "
            "Then, call this tool again with `approved=True`."
        )

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if target_text not in content:
            task_state.log_error(f"edit_file error: target_text not found in {path}")
            return "Error: target_text not found in the file. Read the file again to get the exact string."
            
        new_content = content.replace(target_text, replacement_text, 1)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        task_state.log_file_modified(path)
        response = f"Successfully edited {path}."
        response += _run_automated_tests(path, verify_command)
        return response
    except Exception as e:
        task_state.log_error(f"edit_file error: {str(e)}")
        return f"Error editing file: {str(e)}"

def run_verification(command: str) -> str:
    """Runs a terminal command to verify your recent edits. 
    You MUST call this immediately after editing a file.
    
    Args:
        command: The test or lint command to run (e.g., 'pytest', 'node script.js').
        
    Returns:
        The output of the test. If it fails, you must observe the errors and fix them.
    """
    task_state.log_tool("run_verification")
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
            action = f"Verify Failed: {command}"
            task_state.log_verification(f"❌ Verification failed for command: {command}")
            task_state.log_recovery_attempt(action)
            if task_state.check_recovery_limit(action, limit=3):
                return f"TEST FAILED (Exit code {result.returncode})!\n\n{final_output}\n\n❌ MAXIMUM RECOVERY ATTEMPTS EXCEEDED (3). You must stop running this test and ask the user for human intervention."
            else:
                return f"TEST FAILED (Exit code {result.returncode})! Analyze this output and fix your code:\n\n{final_output}"
        
        task_state.log_verification(f"✅ Verification passed for command: {command}")
        return f"TEST PASSED:\n\n{final_output}"
    except Exception as e:
        task_state.log_error(f"run_verification error: {str(e)}")
        return f"Error verifying: {str(e)}"
        
def list_directory(path: str) -> str:
    """Lists all files and folders in a given directory to help navigate the codebase.
    
    Args:
        path: The path to the directory (use '.' for the current workspace).
        
    Returns:
        A string containing the folder structure, ignoring common hidden folders.
    """
    task_state.log_tool("list_directory")
    try:
        import os
        ignored_dirs = {'.git', '.venv', '__pycache__', 'node_modules', '.chainlit', '.streamlit', '.files'}
        result = []
        
        if not os.path.isdir(path):
            task_state.log_error(f"list_directory error: Invalid directory {path}")
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
        task_state.log_error(f"list_directory error: {str(e)}")
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
    task_state.log_tool("grep_search")
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

def git_checkpoint(message: str, files_to_commit: list[str] = None, approved: bool = False) -> str:
    """Creates a Git commit to save the current state of the code safely."""
    task_state.log_tool("git_checkpoint")
    if not approved:
        files_list = ", ".join(files_to_commit) if files_to_commit else "ALL modified files"
        return (
            "❌ ACTION BLOCKED: You MUST output a message to the user asking for permission to commit these files to Git. "
            f"Files to commit: {files_list}\n"
            "Wait for them to reply 'yes' or 'approved'. "
            "Then, call this tool again with `approved=True`."
        )

    try:
        # Check if git is initialized
        if not os.path.exists(".git"):
            subprocess.run("git init", shell=True, capture_output=True)
            
        if files_to_commit:
            for file in files_to_commit:
                subprocess.run(f'git add "{file}"', shell=True, capture_output=True)
        else:
            subprocess.run("git add .", shell=True, capture_output=True)
            
        result = subprocess.run(f'git commit -m "Agent Checkpoint: {message}"', shell=True, capture_output=True, text=True)
        return "Checkpoint saved! You can now safely edit. If you break it, use git_rollback."
    except Exception as e:
        task_state.log_error(f"git_checkpoint error: {str(e)}")
        return f"Error saving checkpoint: {str(e)}"

def git_rollback() -> str:
    """Reverts the entire codebase back to the last git_checkpoint."""
    task_state.log_tool("git_rollback")
    try:
        task_state.log_recovery_attempt("git_rollback")
        result = subprocess.run("git reset --hard HEAD", shell=True, capture_output=True, text=True)
        subprocess.run("git clean -fd", shell=True, capture_output=True) # Removes untracked files too
        return "Codebase successfully rolled back to the last checkpoint! You have a clean slate."
    except Exception as e:
        task_state.log_error(f"git_rollback error: {str(e)}")
        return f"Error rolling back: {str(e)}"
        
def execute_command(command: str, approved: bool = False) -> str:
    """Executes a shell command on the host system."""
    task_state.log_tool("execute_command")
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
            
        final_output = output.strip() if output.strip() else "Command executed successfully with no output."
        if result.returncode != 0:
            action = f"Command Failed: {command.split()[0]}"
            task_state.log_error(f"Command failed ({result.returncode}): {command}")
            task_state.log_recovery_attempt(action)
            if task_state.check_recovery_limit(action, limit=3):
                return f"❌ COMMAND FAILED (Exit code {result.returncode})!\n\n{final_output}\n\n❌ MAXIMUM RECOVERY ATTEMPTS EXCEEDED (3). You must stop running this command and ask the user for human intervention."
        
        return final_output
    except Exception as e:
        task_state.log_error(f"execute_command error: {str(e)}")
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

def update_plan(task_goal: str, steps: list[str], files_affected: list[str], tools_used: list[str], verification_steps: list[str]) -> str:
    """Creates or updates the structured execution plan."""
    task_state.log_tool("update_plan")
    
    plan = {
        "task_goal": task_goal,
        "steps": steps,
        "files_affected": files_affected,
        "tools_used": tools_used,
        "verification_steps": verification_steps
    }
    
    # Store locally for the user
    os.makedirs("plans", exist_ok=True)
    with open(os.path.join("plans", ".sentinel_plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=4)
        
    # Update the internal state manager
    task_state.data["current_plan"] = plan
    task_state.data["original_goal"] = task_goal
    task_state.save()
    
    return "Plan successfully created/updated and saved as structured data. Proceed with executing the steps."

def update_task_status(step: str, status: str, completion_state: str) -> str:
    """Updates the internal lifecycle status of the task. 
    Use this to mark a task as 'completed' when you finish, or 'failed' if you give up.
    
    Args:
        step: The current step you are on (e.g. 'Writing tests', 'Finished').
        status: The current status (e.g. 'in_progress', 'blocked').
        completion_state: The final outcome (e.g. 'incomplete', 'completed', 'failed').
    """
    task_state.log_tool("update_task_status")
    task_state.data["current_step"] = step
    task_state.data["status"] = status
    task_state.data["completion_state"] = completion_state
    task_state.save()
    return f"Task status updated to: {completion_state} ({status})"

class RepoIndexer:
    def __init__(self, root_dir="."):
        self.root_dir = root_dir
        self.ignored_dirs = {'.git', '.venv', '__pycache__', 'node_modules', '.chainlit', '.streamlit', '.files', 'build', 'dist', '.idea', '.vscode', 'chats', 'plans', 'tasks'}
        self.ignored_exts = {'.pyc', '.exe', '.dll', '.so', '.dylib', '.zip', '.tar', '.gz', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.db', '.sqlite3'}
        self.index_file = "tasks/repo_index.json"
        os.makedirs("tasks", exist_ok=True)
        
    def _extract_ast_info(self, filepath):
        import ast
        info = {
            "classes": {},
            "functions": {},
            "imports": []
        }
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            
            def extract_calls(node):
                calls = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            calls.append(child.func.id)
                        elif isinstance(child.func, ast.Attribute):
                            if isinstance(child.func.value, ast.Name):
                                calls.append(f"{child.func.value.id}.{child.func.attr}")
                            else:
                                calls.append(f"*.{child.func.attr}")
                return list(set(calls))
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                    methods = []
                    for child in node.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            args = [arg.arg for arg in child.args.args]
                            methods.append({"name": child.name, "args": args, "line": child.lineno, "calls": extract_calls(child)})
                    info["classes"][node.name] = {
                        "line": node.lineno,
                        "bases": bases,
                        "methods": methods
                    }
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [arg.arg for arg in node.args.args]
                    decs = []
                    for d in node.decorator_list:
                        if hasattr(ast, 'unparse'): decs.append(ast.unparse(d))
                        elif isinstance(d, ast.Name): decs.append(d.id)
                        else: decs.append("@decorator")
                    info["functions"][node.name] = {
                        "line": node.lineno,
                        "args": args,
                        "decorators": decs,
                        "calls": extract_calls(node)
                    }
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        info["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module if node.module else ""
                    for alias in node.names:
                        info["imports"].append(f"{module}.{alias.name}")
        except Exception as e:
            info["error"] = str(e)
            
        return info

    def build_index(self):
        index = {
            "directories": [],
            "source_files": [],
            "config_files": [],
            "other_files": [],
            "by_extension": {},
            "python_ast": {}
        }
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs and not d.startswith('.')]
            
            rel_root = os.path.relpath(root, self.root_dir)
            if rel_root == ".":
                rel_root = ""
            elif rel_root:
                index["directories"].append(rel_root)
                
            for file in files:
                if any(file.endswith(ext) for ext in self.ignored_exts) or (file.startswith('.') and not file == '.env.example'):
                    continue
                    
                rel_path = os.path.join(rel_root, file) if rel_root else file
                ext = os.path.splitext(file)[1].lower()
                
                if ext not in index["by_extension"]:
                    index["by_extension"][ext] = []
                index["by_extension"][ext].append(rel_path)
                    
                if file in {'requirements.txt', 'package.json', 'pyproject.toml', '.env.example', 'Dockerfile', 'docker-compose.yml', 'app.py', 'tools.py'}:
                    index["config_files"].append(rel_path)
                elif ext in {'.py', '.js', '.ts', '.html', '.css', '.java', '.c', '.cpp', '.rs', '.go', '.md'}:
                    index["source_files"].append(rel_path)
                else:
                    index["other_files"].append(rel_path)
                    
                if ext == '.py':
                    index["python_ast"][rel_path] = self._extract_ast_info(os.path.join(self.root_dir, rel_path))
                    
        # --- Build Dependency Graph ---
        dep_graph = {
            "outbound": {f: [] for f in index.get("python_ast", {})},
            "inbound": {f: [] for f in index.get("python_ast", {})}
        }
        
        # Helper: Create a lookup of module paths to local files (e.g. "tools" -> "tools.py")
        # Python module paths substitute os.sep with dots, minus the extension.
        py_modules = {}
        for f in index.get("python_ast", {}):
            mod_name = f.replace('.py', '').replace(os.sep, '.')
            py_modules[mod_name] = f
            
        for file, info in index.get("python_ast", {}).items():
            for imp in info.get("imports", []):
                parts = imp.split('.')
                resolved = None
                # Resolve from most specific (e.g. tools.AGENT_TOOLS) to least specific (e.g. tools)
                for i in range(len(parts), 0, -1):
                    attempt = ".".join(parts[:i])
                    if attempt in py_modules:
                        resolved = py_modules[attempt]
                        break
                
                # Register the edge if it resolves to a local file in the workspace
                if resolved and resolved != file:
                    if resolved not in dep_graph["outbound"][file]:
                        dep_graph["outbound"][file].append(resolved)
                    if file not in dep_graph["inbound"][resolved]:
                        dep_graph["inbound"][resolved].append(file)
                        
        index["dependency_graph"] = dep_graph
        
        # --- Build Call Graph ---
        call_graph = { "outbound": {}, "inbound": {} }
        
        # 1. Map all known symbols to their file
        symbol_map = {}
        for f, info in index.get("python_ast", {}).items():
            for func_name in info.get("functions", {}):
                sym_id = f"{f}::{func_name}"
                if func_name not in symbol_map: symbol_map[func_name] = []
                symbol_map[func_name].append(sym_id)
                call_graph["outbound"][sym_id] = []
                call_graph["inbound"][sym_id] = []
                
            for cls_name, cls_info in info.get("classes", {}).items():
                for m in cls_info.get("methods", []):
                    m_name = m["name"]
                    sym_id = f"{f}::{cls_name}.{m_name}"
                    full_m = f"{cls_name}.{m_name}"
                    if full_m not in symbol_map: symbol_map[full_m] = []
                    symbol_map[full_m].append(sym_id)
                    if m_name not in symbol_map: symbol_map[m_name] = []
                    symbol_map[m_name].append(sym_id)
                    
                    call_graph["outbound"][sym_id] = []
                    call_graph["inbound"][sym_id] = []

        # 2. Resolve edges
        for f, info in index.get("python_ast", {}).items():
            def resolve_call(call_str):
                if call_str in symbol_map:
                    local_match = [s for s in symbol_map[call_str] if s.startswith(f"{f}::")]
                    if local_match: return local_match[0]
                    if len(symbol_map[call_str]) == 1:
                        return symbol_map[call_str][0]
                
                if '.' in call_str:
                    mod, func = call_str.rsplit('.', 1)
                    if func in symbol_map:
                        for s in symbol_map[func]:
                            s_file = s.split('::')[0]
                            if s_file.replace('.py', '').replace(os.sep, '.').endswith(mod):
                                return s
                return f"?{call_str}"
            
            for func, func_info in info.get("functions", {}).items():
                sym_id = f"{f}::{func}"
                for c in func_info.get("calls", []):
                    target = resolve_call(c)
                    if target:
                        call_graph["outbound"][sym_id].append(target)
                        if not target.startswith("?"):
                            call_graph["inbound"][target].append(sym_id)
                            
            for cls_name, cls_info in info.get("classes", {}).items():
                for m in cls_info.get("methods", []):
                    sym_id = f"{f}::{cls_name}.{m['name']}"
                    for c in m.get("calls", []):
                        if c.startswith("self."):
                            c = c.replace("self.", f"{cls_name}.", 1)
                        target = resolve_call(c)
                        if target:
                            call_graph["outbound"][sym_id].append(target)
                            if not target.startswith("?"):
                                call_graph["inbound"][target].append(sym_id)
                                
        index["call_graph"] = call_graph
        
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=4)
        return index
            
    def query(self, query_type: str = "summary"):
        if not os.path.exists(self.index_file):
            self.build_index()
            
        with open(self.index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
            
        if query_type == "summary":
            ast_count = len(index.get('python_ast', {}))
            return (
                f"Repository Summary:\n"
                f"- Directories: {len(index['directories'])}\n"
                f"- Source Files: {len(index['source_files'])}\n"
                f"- Config/Important Files: {len(index['config_files'])}\n"
                f"- Python AST Parsed Files: {ast_count}\n"
                f"Top Config/Important Files: {', '.join(index['config_files'][:15])}\n"
                f"Extensions: {', '.join([f'{k} ({len(v)})' for k,v in index['by_extension'].items()])}\n"
                f"Use 'source_files', 'config_files', 'directories', 'ast_symbols', 'deps:<filename>', or 'calls:<symbol>' query_type for details."
            )
        elif query_type == "ast_symbols":
            if "python_ast" not in index: return "No AST data found."
            out = []
            for file, info in index["python_ast"].items():
                out.append(f"\n--- {file} ---")
                if "error" in info:
                    out.append(f"  [Parse Error: {info['error']}]")
                    continue
                if info["imports"]:
                    out.append(f"  Imports: {', '.join(info['imports'][:5])}{'...' if len(info['imports'])>5 else ''}")
                for cls, cls_info in info.get("classes", {}).items():
                    bases = f"({', '.join(cls_info['bases'])})" if cls_info['bases'] else ""
                    out.append(f"  Class {cls}{bases} (Line {cls_info['line']}):")
                    for m in cls_info["methods"]:
                        out.append(f"    - def {m['name']}({', '.join(m['args'])}) (Line {m['line']})")
                for func, func_info in info.get("functions", {}).items():
                    decs = "".join([f"@{d} " for d in func_info['decorators']])
                    out.append(f"  Func: {decs}def {func}({', '.join(func_info['args'])}) (Line {func_info['line']})")
            return "\n".join(out)
        elif query_type.startswith("deps:"):
            target_file = query_type.split(":", 1)[1].strip()
            graph = index.get("dependency_graph", {})
            outbound = graph.get("outbound", {}).get(target_file, [])
            inbound = graph.get("inbound", {}).get(target_file, [])
            
            if target_file not in graph.get("outbound", {}):
                return f"No dependency tracking found for '{target_file}' (maybe it is not a parsed python file, or doesn't exist)."
                
            return (
                f"Dependency Graph for {target_file}:\n\n"
                f"Outbound (Imports / Depends on {len(outbound)} local files):\n" +
                ("".join([f"  -> {x}\n" for x in outbound]) if outbound else "  (None)\n") +
                f"\nInbound (Imported by / Downstream dependents {len(inbound)} local files):\n" +
                ("".join([f"  <- {x}\n" for x in inbound]) if inbound else "  (None)\n")
            )
        elif query_type.startswith("calls:"):
            target_symbol = query_type.split(":", 1)[1].strip()
            graph = index.get("call_graph", {})
            outbound = graph.get("outbound", {}).get(target_symbol, [])
            inbound = graph.get("inbound", {}).get(target_symbol, [])
            
            if target_symbol not in graph.get("outbound", {}):
                return f"No call graph tracking found for '{target_symbol}'. Make sure you provide the exact symbol format: <filename>::<symbol> (e.g. app.py::get_or_create_session)."
                
            outbound_res = [x for x in outbound if not x.startswith("?")]
            outbound_unres = [x for x in outbound if x.startswith("?")]
            
            return (
                f"Call Graph for {target_symbol}:\n\n"
                f"Calls (Outbound statically resolved - {len(outbound_res)}):\n" +
                ("".join([f"  -> {x}\n" for x in outbound_res]) if outbound_res else "  (None)\n") +
                (f"\nCalls (Outbound statically unresolved - {len(outbound_unres)}):\n" +
                "".join([f"  -> {x}\n" for x in outbound_unres]) if outbound_unres else "") +
                f"\nCalled By (Inbound statically resolved - {len(inbound)}):\n" +
                ("".join([f"  <- {x}\n" for x in inbound]) if inbound else "  (None)\n")
            )
        elif query_type.startswith("impact:"):
            target = query_type.split(":", 1)[1].strip()
            is_symbol = "::" in target
            
            direct_impacts = set()
            indirect_impacts = set()
            uncertain_impacts = set()
            
            if is_symbol:
                graph = index.get("call_graph", {})
                file_target = target.split("::")[0]
                
                # Direct callers
                callers = graph.get("inbound", {}).get(target, [])
                direct_impacts.update(callers)
                
                # Indirect callers (callers of callers)
                for caller in callers:
                    indirect_impacts.update(graph.get("inbound", {}).get(caller, []))
                    
                indirect_impacts -= direct_impacts
                indirect_impacts.discard(target)
                
                # Uncertain impacts: files that import the file containing the symbol, 
                # but might call it dynamically or via unresolved references.
                file_deps = index.get("dependency_graph", {}).get("inbound", {}).get(file_target, [])
                uncertain_impacts.update(file_deps)
                
                target_type = "Symbol"
            else:
                graph = index.get("dependency_graph", {})
                
                # Direct dependents (files that import this file)
                deps = graph.get("inbound", {}).get(target, [])
                direct_impacts.update(deps)
                
                # Indirect dependents
                for dep in deps:
                    indirect_impacts.update(graph.get("inbound", {}).get(dep, []))
                    
                indirect_impacts -= direct_impacts
                indirect_impacts.discard(target)
                
                target_type = "File"
                
            report = (
                f"=== IMPACT ANALYSIS REPORT ===\n"
                f"Target {target_type}: {target}\n\n"
                f"Note: This is a static analysis report. Statically unresolved or dynamic relationships might not be listed.\n\n"
            )
            
            if not direct_impacts and not indirect_impacts and not uncertain_impacts:
                report += "No statically known impacts detected. (Target might be an entry-point, dead code, or not found).\n"
                return report
                
            report += "DIRECT IMPACT (Statically known callers/dependents):\n"
            for item in sorted(direct_impacts):
                report += f"  - {item}\n"
            if not direct_impacts:
                report += "  (None detected)\n"
                
            report += "\nINDIRECT IMPACT (Downstream callers/dependents):\n"
            for item in sorted(indirect_impacts):
                report += f"  - {item}\n"
            if not indirect_impacts:
                report += "  (None detected)\n"
                
            if is_symbol and uncertain_impacts:
                report += "\nUNCERTAIN/INDIRECT FILE IMPACT (Files importing this module that might dynamically use this symbol):\n"
                statically_known_files = {x.split('::')[0] for x in direct_impacts | indirect_impacts}
                uncertain = uncertain_impacts - statically_known_files
                for item in sorted(uncertain):
                    report += f"  - {item}\n"
                if not uncertain:
                    report += "  (None detected)\n"
                    
            report += "\nPLANNING RECOMMENDATIONS:\n"
            report += " - Inspect the Direct Impacts before making breaking changes to the target.\n"
            report += " - Verification tests should cover the Direct and Indirect Impacts.\n"
            report += " - If the target's signature or behavior changes, these downstream components may require modification.\n"
            
            return report
        elif query_type in index:
            return "\n".join(index[query_type]) if index[query_type] else "None found."
        else:
            return f"Invalid query_type. Valid types: summary, source_files, config_files, directories, other_files, ast_symbols, deps:<filename>, calls:<symbol>, impact:<target>"

def query_repo_index(query_type: str = "summary", refresh: bool = False) -> str:
    """Queries the repository index to quickly understand the project structure without guessing file paths.
    
    Args:
        query_type: What to query. Options: 'summary', 'source_files', 'config_files', 'directories', 'ast_symbols', 'deps:<filename>', 'calls:<symbol>', or 'impact:<target>'. 
                    Use 'impact:<target>' to run an impact analysis on a file or symbol before modifying it (e.g. impact:app.py::chat or impact:tools.py).
        refresh: Set to True to rebuild the index if files were recently created/deleted.
        
    Returns:
        Structured text from the repository index.
    """
    task_state.log_tool("query_repo_index")
    indexer = RepoIndexer()
    if refresh:
        indexer.build_index()
    return indexer.query(query_type)

# List of all tools to be passed to the agent
AGENT_TOOLS = [read_file, create_file, edit_file, run_verification, list_directory, grep_search, query_repo_index, git_checkpoint, git_rollback, execute_command, search_web, run_python_code, update_plan, update_task_status]
