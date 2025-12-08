"""
AI Agent module for analyzing and modifying vault files.
"""

import json
from typing import Optional
from openai import OpenAI
from .vault import VaultManager, VaultFile


SYSTEM_PROMPT = """You are an intelligent assistant for managing an Obsidian vault. You help users analyze, organize, and modify their markdown notes.

You have access to the following tools to interact with the vault:

1. **list_files** - List all files in the vault, optionally filtered by a glob pattern
2. **read_file** - Read the content of a specific file
3. **write_file** - Write or update content to a file
4. **search** - Search for files containing specific text
5. **tree** - Show the vault's folder structure
6. **list_tags** - List all tags used across the entire vault with file counts
7. **list_yaml_keys** - List all unique YAML frontmatter keys across the entire vault with file counts

When the user asks you to modify files:
- Always show what changes you plan to make before executing
- Be careful with destructive operations
- Preserve existing content unless explicitly asked to remove it
- Maintain proper markdown formatting

When analyzing files:
- Look for patterns, connections between notes, and opportunities for improvement
- Suggest relevant tags, links, or organizational changes
- Identify incomplete notes or areas that could be expanded

Always explain your actions and provide helpful context about what you're doing."""


class VaultAgent:
    """AI-powered agent for interacting with an Obsidian vault."""
    
    def __init__(self, vault_path: str, api_key: str, model: str = "gpt-5.1"):
        self.vault = VaultManager(vault_path)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.conversation_history = []
        self._vault_index = None
        
        # Define tools for OpenAI
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List all markdown files in the vault. Optionally filter by a glob pattern (e.g., '*.md', 'projects/*.md', '**/daily/*.md').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Optional glob pattern to filter files"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the full content of a specific file from the vault.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The relative path to the file within the vault"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file in the vault. This will create the file if it doesn't exist, or overwrite it if it does.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The relative path where to write the file"
                            },
                            "content": {
                                "type": "string",
                                "description": "The markdown content to write"
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search for files containing specific text.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The text to search for"
                            },
                            "case_sensitive": {
                                "type": "boolean",
                                "description": "Whether the search should be case-sensitive"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tree",
                    "description": "Show the folder structure of the vault as a tree.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum depth to show (default: 3)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tags",
                    "description": "List all tags used across the entire vault. Returns every tag (both #inline-tags and YAML frontmatter tags) with the count of files using each tag.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_yaml_keys",
                    "description": "List all unique YAML frontmatter keys across the entire vault with the count of files using each key.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
    
    def _build_vault_index(self) -> str:
        """Scan the vault once to provide a default full-scope summary."""
        files = self.vault.list_files()
        tags = self.vault.list_tags()
        yaml_keys = self.vault.list_yaml_keys()

        lines = []
        lines.append("Vault Index (auto-scanned at conversation start)")
        lines.append(f"- Files: {len(files)}")
        if files:
            lines.append("  File list:")
            for f in files:
                lines.append(f"    - {f.relative_path}")
        lines.append(f"- Tags: {len(tags)}")
        if tags:
            for tag, file_list in tags.items():
                lines.append(f"    - #{tag} ({len(file_list)} files)")
        lines.append(f"- YAML keys: {len(yaml_keys)}")
        if yaml_keys:
            for key, file_list in yaml_keys.items():
                lines.append(f"    - {key} ({len(file_list)} files)")
        return "\n".join(lines)
    
    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return the result."""
        try:
            if tool_name == "list_files":
                files = self.vault.list_files(tool_input.get("pattern"))
                if not files:
                    return "No files found matching the criteria."
                result = f"Found {len(files)} file(s):\n\n"
                for f in files:
                    result += f"- {f.relative_path}\n"
                return result
            
            elif tool_name == "read_file":
                file = self.vault.read_file(tool_input["path"])
                if not file:
                    return f"Error: File not found: {tool_input['path']}"
                return f"**File: {file.relative_path}**\n\n```markdown\n{file.content}\n```"
            
            elif tool_name == "write_file":
                success = self.vault.write_file(tool_input["path"], tool_input["content"])
                if success:
                    return f"✅ Successfully wrote to: {tool_input['path']}"
                return f"❌ Failed to write to: {tool_input['path']}"
            
            elif tool_name == "search":
                files = self.vault.search_content(
                    tool_input["query"],
                    tool_input.get("case_sensitive", False)
                )
                if not files:
                    return f"No files found containing: {tool_input['query']}"
                result = f"Found {len(files)} file(s) containing '{tool_input['query']}':\n\n"
                for f in files:
                    result += f"- {f.relative_path}\n"
                return result
            
            elif tool_name == "tree":
                return self.vault.get_file_tree(tool_input.get("max_depth", 3))
            
            elif tool_name == "list_tags":
                tags = self.vault.list_tags()
                if not tags:
                    return "No tags found in the vault."
                result = f"Found {len(tags)} unique tag(s) across the vault:\n\n"
                for tag, files in tags.items():
                    result += f"- #{tag} ({len(files)} file{'s' if len(files) != 1 else ''})\n"
                return result

            elif tool_name == "list_yaml_keys":
                keys = self.vault.list_yaml_keys()
                if not keys:
                    return "No YAML frontmatter keys found in the vault."
                result = f"Found {len(keys)} unique YAML frontmatter key(s) across the vault:\n\n"
                for key, files in keys.items():
                    result += f"- {key} ({len(files)} file{'s' if len(files) != 1 else ''})\n"
                return result
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    def chat(self, user_message: str) -> str:
        """Send a message and get a response, handling tool calls."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        # Build full-scope vault index once per conversation
        if self._vault_index is None:
            self._vault_index = self._build_vault_index()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": self._vault_index},
        ] + self.conversation_history
        
        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            # Add assistant message to history
            self.conversation_history.append(assistant_message.model_dump())
            messages.append(assistant_message.model_dump())
            
            # Check if there are tool calls
            if assistant_message.tool_calls:
                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    result = self._execute_tool(function_name, function_args)
                    
                    # Add tool result to messages
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    }
                    self.conversation_history.append(tool_message)
                    messages.append(tool_message)
                
                # Continue the loop to get the final response
                continue
            
            # No tool calls, return the response
            return assistant_message.content or ""
    
    def reset_conversation(self):
        """Clear the conversation history."""
        self.conversation_history = []
        self._vault_index = None
