#!/usr/bin/env python3
import os
import sys
import inspect
import importlib.util
import types
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Union
import json
import datetime
from pydantic import BaseModel, Field

# Add the project root to path to find the tools
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import OpenAI Agent SDK
from agents import Agent, function_tool

# Model for tool execution
class ToolArguments(BaseModel):
    """Arguments for executing a Python tool."""
    tool_name: str = Field(..., description="The name of the registered tool to execute")
    string_args: Dict[str, str] = Field(default_factory=dict, description="String arguments to pass to the tool")
    int_args: Dict[str, int] = Field(default_factory=dict, description="Integer arguments to pass to the tool")
    float_args: Dict[str, float] = Field(default_factory=dict, description="Float arguments to pass to the tool")
    bool_args: Dict[str, bool] = Field(default_factory=dict, description="Boolean arguments to pass to the tool")

class CodeContext:
    """Memory/context manager for the CodeAgent."""
    
    def __init__(self, context_file_path: Optional[str] = None):
        """Initialize the context system with optional file path for persistence."""
        self.memory: Dict[str, Any] = {}
        self.context_file_path = context_file_path
        
        # Load persisted context if available
        if context_file_path and os.path.exists(context_file_path):
            try:
                with open(context_file_path, 'r') as f:
                    self.memory = json.load(f)
            except Exception as e:
                print(f"Error loading context file: {e}", file=sys.stderr)
    
    def save(self) -> bool:
        """Save context to the file system if a path is configured."""
        if not self.context_file_path:
            return False
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.context_file_path), exist_ok=True)
            
            with open(self.context_file_path, 'w') as f:
                json.dump(self.memory, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving context: {e}", file=sys.stderr)
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from memory with optional default."""
        return self.memory.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in memory and save if persistence is enabled."""
        self.memory[key] = value
        if self.context_file_path:
            self.save()
    
    def delete(self, key: str) -> bool:
        """Delete a key from memory if it exists."""
        if key in self.memory:
            del self.memory[key]
            if self.context_file_path:
                self.save()
            return True
        return False
    
    def list_keys(self) -> List[str]:
        """Return all keys stored in memory."""
        return list(self.memory.keys())
    
    def clear(self) -> None:
        """Clear all memory."""
        self.memory = {}
        if self.context_file_path:
            self.save()

# Create tool definitions that will be used by the agent
@function_tool
def write_python_code(file_path: str, code: str) -> Dict[str, Any]:
    """
    Write Python code to a file.
    
    Args:
        file_path: The path where the Python file should be created or updated
        code: The Python code to write to the file
        
    Returns:
        A dictionary with status information
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Write the code to the file
        with open(file_path, 'w') as f:
            f.write(code)
            
        return {
            "status": "success",
            "message": f"Successfully wrote code to {file_path}",
            "file_path": file_path
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to write code: {str(e)}",
            "error": str(e)
        }

@function_tool
def read_python_file(file_path: str) -> Dict[str, Any]:
    """
    Read Python code from a file.
    
    Args:
        file_path: The path to the Python file to read
        
    Returns:
        A dictionary with the file content and status information
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        return {
            "status": "success",
            "content": content,
            "file_path": file_path
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to read file: {str(e)}",
            "error": str(e)
        }

@function_tool
def register_python_code_as_tool(code: str, function_name: str) -> Dict[str, Any]:
    """
    Register Python code as a dynamically available tool.
    
    Args:
        code: The Python code that defines a function to be used as a tool
        function_name: The name of the function to extract from the code
        
    Returns:
        A dictionary with status information about the tool registration
    """
    try:
        # Create a namespace to execute the code
        namespace = {}
        
        # Execute the code in the namespace
        exec(code, namespace)
        
        # Check if the function exists in the namespace
        if function_name not in namespace:
            return {
                "status": "error",
                "message": f"Function '{function_name}' not found in the provided code"
            }
        
        # Get the function
        func = namespace[function_name]
        
        # Verify it's callable
        if not callable(func):
            return {
                "status": "error",
                "message": f"'{function_name}' is not a callable function"
            }
        
        # Store the function in the agent's dynamic tools registry
        # This will be handled by the CodeAgent class
        
        # Return success with the function's signature
        signature = inspect.signature(func)
        docstring = inspect.getdoc(func) or "No documentation available"
        
        return {
            "status": "success",
            "message": f"Successfully registered function '{function_name}' as a tool",
            "function_name": function_name,
            "signature": str(signature),
            "docstring": docstring
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to register tool: {str(e)}",
            "error": str(e)
        }

@function_tool
def execute_python_tool(
    tool_name: str,
    string_args: Dict[str, str] = None,
    int_args: Dict[str, int] = None,
    float_args: Dict[str, float] = None,
    bool_args: Dict[str, bool] = None
) -> Dict[str, Any]:
    """
    Execute a previously registered Python tool.
    
    Args:
        tool_name: The name of the registered tool to execute
        string_args: String arguments to pass to the tool
        int_args: Integer arguments to pass to the tool
        float_args: Float arguments to pass to the tool
        bool_args: Boolean arguments to pass to the tool
        
    Returns:
        A dictionary with the result of the tool execution and status information
    """
    # This will be handled by the CodeAgent class
    return {
        "status": "pending",
        "message": "Tool execution will be handled by the CodeAgent"
    }

@function_tool
def set_context(key: str, value: Any) -> Dict[str, Any]:
    """
    Store a value in the agent's context/memory.
    
    Args:
        key: The key to store the value under
        value: The value to store (must be JSON serializable)
        
    Returns:
        A dictionary with status information
    """
    # This will be handled by the CodeAgent class
    return {
        "status": "pending", 
        "message": "Context storage will be handled by the CodeAgent"
    }

@function_tool
def get_context(key: str) -> Dict[str, Any]:
    """
    Retrieve a value from the agent's context/memory.
    
    Args:
        key: The key to retrieve
        
    Returns:
        A dictionary with the retrieved value and status information
    """
    # This will be handled by the CodeAgent class
    return {
        "status": "pending",
        "message": "Context retrieval will be handled by the CodeAgent"
    }

@function_tool
def list_context_keys() -> Dict[str, Any]:
    """
    List all keys stored in the agent's context/memory.
    
    Returns:
        A dictionary with a list of all stored keys
    """
    # This will be handled by the CodeAgent class
    return {
        "status": "pending",
        "message": "Context listing will be handled by the CodeAgent"
    }

@function_tool
def delete_context(key: str) -> Dict[str, Any]:
    """
    Delete a key from the agent's context/memory.
    
    Args:
        key: The key to delete
        
    Returns:
        A dictionary with status information
    """
    # This will be handled by the CodeAgent class
    return {
        "status": "pending",
        "message": "Context deletion will be handled by the CodeAgent"
    }

class CodeAgent:
    """Agent that can write, execute, and manage Python code as tools."""
    
    def __init__(self, context_file_path: Optional[str] = None):
        """Initialize the code agent with optional persistent context."""
        self.context = CodeContext(context_file_path)
        self.dynamic_tools: Dict[str, Callable] = {}
        
        # Define the actual tools that implement the functionality
        self._actual_tools = {
            "set_context": self._set_context,
            "get_context": self._get_context,
            "list_context_keys": self._list_context_keys,
            "delete_context": self._delete_context,
            "execute_python_tool": self._execute_python_tool,
            "register_python_code_as_tool": self._register_python_code_as_tool
        }
        
        # Create the agent with all tools
        self.agent = Agent(
            name="Code Agent",
            instructions="""
            You are a Code Agent with the ability to write, read, and execute Python code.
            You can dynamically create tools by writing Python functions and then register them for use.
            You also have access to a persistent memory/context system to store and retrieve data.
            
            Your capabilities include:
            1. Writing Python code to files
            2. Reading Python code from files
            3. Registering Python functions as executable tools
            4. Executing previously registered tools
            5. Storing data in your memory context
            6. Retrieving data from your memory context
            
            When executing code, be careful to handle errors properly and provide clear feedback.
            When you register a function as a tool, it should be well-documented and include type hints.
            
            Workflow for creating and using dynamic tools:
            1. Write a Python function using `write_python_code` or directly with `register_python_code_as_tool`
            2. Register the function using `register_python_code_as_tool`
            3. Execute the function using `execute_python_tool` with the appropriate parameters
            
            For storing and retrieving data:
            1. Use `set_context` to store data
            2. Use `get_context` to retrieve previously stored data
            3. Use `list_context_keys` to see what data is available
            4. Use `delete_context` to remove data you no longer need
            """,
            tools=[
                write_python_code,
                read_python_file,
                register_python_code_as_tool, 
                execute_python_tool,
                set_context,
                get_context,
                list_context_keys,
                delete_context
            ],
            # DO NOT CHANGE THIS MODEL FROM THE CURRENT SETTING
            model="gpt-4o-mini-2024-07-18",
        )
    
    def _set_context(self, key: str, value: Any) -> Dict[str, Any]:
        """Actual implementation of set_context."""
        try:
            self.context.set(key, value)
            return {
                "status": "success",
                "message": f"Successfully stored value under key '{key}'",
                "key": key
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to store context: {str(e)}",
                "error": str(e)
            }
    
    def _get_context(self, key: str) -> Dict[str, Any]:
        """Actual implementation of get_context."""
        try:
            value = self.context.get(key)
            if value is None:
                return {
                    "status": "error",
                    "message": f"Key '{key}' not found in context",
                    "key": key
                }
            return {
                "status": "success",
                "message": f"Successfully retrieved value for key '{key}'",
                "key": key,
                "value": value
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to retrieve context: {str(e)}",
                "error": str(e)
            }
    
    def _list_context_keys(self) -> Dict[str, Any]:
        """Actual implementation of list_context_keys."""
        try:
            keys = self.context.list_keys()
            return {
                "status": "success",
                "message": f"Found {len(keys)} keys in context",
                "keys": keys
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to list context keys: {str(e)}",
                "error": str(e)
            }
    
    def _delete_context(self, key: str) -> Dict[str, Any]:
        """Actual implementation of delete_context."""
        try:
            deleted = self.context.delete(key)
            if deleted:
                return {
                    "status": "success",
                    "message": f"Successfully deleted key '{key}' from context",
                    "key": key
                }
            else:
                return {
                    "status": "error",
                    "message": f"Key '{key}' not found in context",
                    "key": key
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete context: {str(e)}",
                "error": str(e)
            }
    
    def _register_python_code_as_tool(self, code: str, function_name: str) -> Dict[str, Any]:
        """Actual implementation of register_python_code_as_tool."""
        try:
            # Create a namespace to execute the code
            namespace = {}
            
            # Execute the code in the namespace
            exec(code, namespace)
            
            # Check if the function exists in the namespace
            if function_name not in namespace:
                return {
                    "status": "error",
                    "message": f"Function '{function_name}' not found in the provided code"
                }
            
            # Get the function
            func = namespace[function_name]
            
            # Verify it's callable
            if not callable(func):
                return {
                    "status": "error",
                    "message": f"'{function_name}' is not a callable function"
                }
            
            # Store the function in the dynamic tools registry
            self.dynamic_tools[function_name] = func
            
            # Also store the code in context for future reference
            self.context.set(f"tool_code_{function_name}", code)
            
            # Return success with the function's signature
            signature = inspect.signature(func)
            docstring = inspect.getdoc(func) or "No documentation available"
            
            return {
                "status": "success",
                "message": f"Successfully registered function '{function_name}' as a tool",
                "function_name": function_name,
                "signature": str(signature),
                "docstring": docstring
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to register tool: {str(e)}",
                "error": str(e),
                "traceback": str(sys.exc_info())
            }
    
    def _execute_python_tool(
        self, 
        tool_name: str,
        string_args: Dict[str, str] = None,
        int_args: Dict[str, int] = None,
        float_args: Dict[str, float] = None,
        bool_args: Dict[str, bool] = None
    ) -> Dict[str, Any]:
        """Actual implementation of execute_python_tool."""
        try:
            # Check if the tool exists
            if tool_name not in self.dynamic_tools:
                return {
                    "status": "error",
                    "message": f"Tool '{tool_name}' not found. Available tools: {list(self.dynamic_tools.keys())}"
                }
            
            # Get the tool function
            tool_func = self.dynamic_tools[tool_name]
            
            # Combine all arguments
            arguments = {}
            if string_args:
                arguments.update(string_args)
            if int_args:
                arguments.update(int_args)
            if float_args:
                arguments.update(float_args)
            if bool_args:
                arguments.update(bool_args)
            
            # Execute the tool with the provided arguments
            start_time = datetime.datetime.now()
            result = tool_func(**arguments)
            end_time = datetime.datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Return the result with execution information
            return {
                "status": "success",
                "message": f"Successfully executed tool '{tool_name}'",
                "tool_name": tool_name,
                "execution_time_seconds": execution_time,
                "result": result
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to execute tool '{tool_name}': {str(e)}",
                "tool_name": tool_name,
                "error": str(e),
                "traceback": str(sys.exc_info())
            }
    
    def handle_tool_call(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Handle calls to the tool by routing to the actual implementation."""
        if tool_name in self._actual_tools:
            # Handle the tool call directly
            return self._actual_tools[tool_name](**kwargs)
        return {
            "status": "error",
            "message": f"Unknown tool: {tool_name}"
        }
    
    async def run(self, prompt: str):
        """Run the code agent on a given prompt."""
        from agents import Runner
        
        # Override the tools to intercept the calls
        original_tools = {}
        for tool_name in self._actual_tools:
            for i, tool in enumerate(self.agent.tools):
                if tool.name == tool_name:
                    # Save the original tool
                    original_tools[tool_name] = self.agent.tools[i]
                    
                    # Create a new tool function that intercepts the call
                    async def intercepted_tool_call(tool_name=tool_name, **kwargs):
                        return self.handle_tool_call(tool_name, **kwargs)
                    
                    # Replace the tool implementation
                    self.agent.tools[i].implementation = intercepted_tool_call
        
        try:
            # Run the agent with the prompt
            result = await Runner.run(self.agent, prompt)
            return result
        finally:
            # Restore the original tools
            for tool_name, original_tool in original_tools.items():
                for i, tool in enumerate(self.agent.tools):
                    if tool.name == tool_name:
                        self.agent.tools[i].implementation = original_tool.implementation

# Example of how this agent might be run
if __name__ == '__main__':
    import asyncio
    
    async def test_code_agent():
        # Create a code agent with persistent context
        context_path = os.path.join(project_root, "data", "code_agent_context.json")
        code_agent = CodeAgent(context_path)
        
        # Test prompt
        prompt = "Write a Python function called 'add_numbers' that adds two numbers together, then register it as a tool and execute it with numbers 5 and 10."
        
        print("\n--- Running Code Agent ---")
        result = await code_agent.run(prompt)
        print("\n--- Code Agent Result ---")
        print(result.final_output)
    
    # Run the test
    asyncio.run(test_code_agent())