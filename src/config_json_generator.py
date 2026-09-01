# SAPÉ f-MCP — controlled file system access with granular permissions for LLMs
# Copyright (C) 2026 Luciano Arrezze
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-only

"""Generate MCP configuration JSON for various LLM platforms."""

import json
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigJSONGenerator:
    """Generate comprehensive MCP configuration as JSON for LLM integration.

    Provides configuration snippets for:
    - Claude (claude.ai)
    - OpenAI ChatGPT (custom actions)
    - Anthropic API (direct API integration)
    - Google Gemini (custom system instructions)
    - Ollama (local models)
    - Generic LLMs (adapter pattern)
    """

    #: Server name written into client configuration files. The setup wizard
    #: uses the same one, so a user who follows both paths registers one server
    #: rather than two copies of it.
    CLIENT_SERVER_NAME = 'sape-f-mcp'

    def __init__(self, server):
        """Initialize generator with FileMCPServer instance.

        Args:
            server: FileMCPServer instance providing port, permissions, and tool info
        """
        self.server = server
        self.port = getattr(server, 'port', 8089)
        self.app_path = Path(__file__).resolve().parent.parent / "main.py"

    def generate(self) -> dict:
        """Generate comprehensive MCP config as dictionary.

        Returns:
            dict: Configuration structure with servers, tools, permissions, and setup instructions
        """
        return {
            'mcpServers': self._generate_mcp_servers(),
            'server': self._generate_server_info(),
            'tools': self._generate_tools_list(),
            'permissions': self._generate_permissions_list(),
            'setup_instructions': self._generate_setup_instructions()
        }

    def _generate_mcp_servers(self) -> dict:
        """Generate MCP servers configuration.

        Delegates to :class:`~src.mcp_config_generator.MCPConfigGenerator` so
        this page and the MCP Configuration wizard cannot disagree about how to
        start the server — and so the command is the interpreter running this
        window rather than a bare ``python``, which in a client environment
        usually cannot import the package.

        Returns:
            dict: MCP server definitions for stdio and streamable-http transports
        """
        from src.mcp_config_generator import MCPConfigGenerator

        generator = MCPConfigGenerator()
        installation = generator.detect_installation()
        db_path = getattr(getattr(self.server, 'permissions', None), 'db_path', None)

        try:
            stdio = generator.generate_config(installation, db_path=db_path)
            http = generator.generate_config(
                installation, db_path=db_path, transport='streamable-http'
            )
        except ValueError as exc:
            logger.error(f"Cannot generate MCP server configuration: {exc}")
            return {'_error': str(exc)}

        stdio['description'] = 'SAPÉ f-MCP server via stdio (for Claude Desktop, Anthropic API, Ollama)'
        http['description'] = 'SAPÉ f-MCP server via streamable-http (for OpenAI, Gemini, or custom integrations)'
        return {'sape-f-mcp-stdio': stdio, 'sape-f-mcp-http': http}

    def _generate_server_info(self) -> dict:
        """Generate server connection information.

        Returns:
            dict: Server address and transport details
        """
        return {
            'address': f'localhost:{self.port}',
            'transport': 'stdio',
            'description': 'SAPÉ f-MCP permission-controlled file system access',
            'tools_count': len(self._generate_tools_list()),
            'permissions_count': len(self._generate_permissions_list())
        }

    def _generate_tools_list(self) -> List[dict]:
        """Generate comprehensive tools list with descriptions and parameters.

        Returns:
            list: Tool definitions for all 11 MCP operations
        """
        return [
            {
                'name': 'create',
                'description': 'Create a new file or directory',
                'parameters': {
                    'path': {'type': 'string', 'description': 'File or directory path'},
                    'directory': {'type': 'boolean', 'description': 'True for directory, False for file'},
                    'content': {'type': 'string', 'description': 'Initial file content (files only)'},
                    'overwrite': {'type': 'boolean', 'description': 'Allow replacing an existing file'}
                }
            },
            {
                'name': 'delete',
                'description': 'Delete a file or directory (recursive delete requires all permissions)',
                'parameters': {
                    'path': {'type': 'string', 'description': 'File or directory path'},
                    'recursive': {'type': 'boolean', 'description': 'Recursively delete directories'}
                }
            },
            {
                'name': 'move',
                'description': 'Move or rename a file or directory',
                'parameters': {
                    'source': {'type': 'string', 'description': 'Source path'},
                    'destination': {'type': 'string', 'description': 'Destination path'},
                    'overwrite': {'type': 'boolean', 'description': 'Allow replacing an existing destination'}
                }
            },
            {
                'name': 'copy',
                'description': 'Copy a file or directory (recursive copy requires destination permission)',
                'parameters': {
                    'source': {'type': 'string', 'description': 'Source path'},
                    'destination': {'type': 'string', 'description': 'Destination path'},
                    'recursive': {'type': 'boolean', 'description': 'Recursively copy directories'},
                    'overwrite': {'type': 'boolean', 'description': 'Allow replacing an existing destination'}
                }
            },
            {
                'name': 'list',
                'description': 'List directory contents with optional filtering and recursion',
                'parameters': {
                    'path': {'type': 'string', 'description': 'Directory path'},
                    'recursive': {'type': 'boolean', 'description': 'List subdirectories recursively'},
                    'include_hidden': {'type': 'boolean', 'description': 'Include hidden files/directories'}
                }
            },
            {
                'name': 'read',
                'description': 'Read file contents as text',
                'parameters': {
                    'path': {'type': 'string', 'description': 'File path'},
                    'encoding': {'type': 'string', 'description': "Text encoding (default: utf-8); pass 'base64' for binary files"}
                }
            },
            {
                'name': 'edit',
                'description': 'Edit text file content (replace/append/overwrite modes)',
                'parameters': {
                    'path': {'type': 'string', 'description': 'File path'},
                    'mode': {'type': 'string', 'enum': ['replace', 'append', 'overwrite'],
                             'description': 'Edit mode: replace (exact match), append, or overwrite'},
                    'old_string': {'type': 'string', 'description': 'Exact text to find (required for replace mode)'},
                    'content': {'type': 'string', 'description': 'Replacement text, text to append, or the new file content'},
                    'replace_all': {'type': 'boolean', 'description': 'Replace every occurrence instead of requiring a unique match'}
                }
            },
            {
                'name': 'chmod',
                'description': 'Set Unix permissions (octal notation)',
                'parameters': {
                    'path': {'type': 'string', 'description': 'File or directory path'},
                    'mode': {'type': 'string', 'description': 'Octal permission (e.g., "644" or "0o755")'},
                    'recursive': {'type': 'boolean', 'description': 'Apply recursively to directory contents'}
                }
            },
            {
                'name': 'download',
                'description': 'Copy a file or directory to a staging directory and return its path',
                'parameters': {
                    'path': {'type': 'string', 'description': 'File or directory path to download'}
                }
            },
            {
                'name': 'upload',
                'description': 'Upload base64-encoded file content',
                'parameters': {
                    'path': {'type': 'string', 'description': 'Destination file path'},
                    'content': {'type': 'string', 'description': 'File content, base64-encoded unless encoding says otherwise'},
                    'encoding': {'type': 'string', 'description': "Content encoding: 'base64' (default) or a text codec such as 'utf-8'"},
                    'overwrite': {'type': 'boolean', 'description': 'Allow replacing an existing file'}
                }
            },
            {
                'name': 'show-permissions',
                'description': 'Display all current permission rules',
                'parameters': {}
            }
        ]

    def _generate_permissions_list(self) -> List[dict]:
        """Generate current permission rules from the server.

        Returns:
            list: Current permission rules from database
        """
        try:
            rules = self.server.permissions.rules()
            return [
                {
                    'path': rule['path'],
                    'actions': [
                        action for action in ['create', 'delete', 'move', 'copy', 'list', 'read', 'edit', 'chmod', 'download', 'upload']
                        if rule.get(f'can_{action}', False)
                    ] or ['none'],
                    'allow_subfolders': bool(rule.get('allow_subfolders', False)),
                    'user_created': rule.get('user_created', 'unknown'),
                    'created_at': rule.get('created_at', 'unknown')
                }
                for rule in rules
            ]
        except Exception as e:
            return [{'error': f'Could not retrieve permissions: {e}'}]

    def _generate_setup_instructions(self) -> dict:
        """Generate setup instructions for all supported LLM platforms.

        Returns:
            dict: Platform-specific setup guides
        """
        return {
            'claude_ai': self._instructions_claude_ai(),
            'openai_chatgpt': self._instructions_openai_chatgpt(),
            'anthropic_api': self._instructions_anthropic_api(),
            'google_gemini': self._instructions_google_gemini(),
            'ollama': self._instructions_ollama(),
            'generic_llms': self._instructions_generic_llms()
        }

    def _instructions_claude_ai(self) -> dict:
        """Generate setup instructions for Claude (claude.ai).

        Returns:
            dict: Step-by-step configuration for Claude Desktop
        """
        return {
            'platform': 'Claude (claude.ai)',
            'type': 'Web/Desktop',
            'steps': [
                'Go to claude.ai and log in',
                'Click your profile (bottom left) → Settings → Files & integrations',
                'Look for "Tools" or "Custom integrations" section',
                'If available, you can add a custom MCP server URL',
                'Otherwise, use Claude Desktop app (local client) for full MCP support'
            ],
            'claude_desktop_setup': {
                'config_file': {
                    'windows': '%APPDATA%\\Claude\\claude_desktop_config.json',
                    'macos': '~/Library/Application Support/Claude/claude_desktop_config.json',
                    'linux': '~/.config/Claude/claude_desktop_config.json'
                },
                'json_content': {
                    'mcpServers': {
                        'sape-f-mcp': {
                            'command': 'python',
                            'args': [str(self.app_path), '--cli'],
                            'env': {}
                        }
                    }
                },
                'instructions': [
                    '1. Install Claude Desktop from https://claude.ai/desktop',
                    '2. Find the config file path above for your OS',
                    '3. Create/edit the JSON file with the content shown above',
                    '4. Replace <path-to-main.py> with actual path to main.py',
                    '5. Restart Claude Desktop',
                    '6. In Claude, you can now use tools like: create("./myfile.txt", content="Hello")',
                    'Note: SAPÉ f-MCP will be available as an MCP tool in the Tools panel'
                ]
            },
            'common_pitfalls': [
                'JSON syntax errors in config file (invalid quotes, missing commas)',
                'Wrong path to main.py (use absolute path, not relative)',
                'Python not in system PATH (use full python.exe path on Windows)',
                'Config file location not found (check OS-specific paths above)',
                'Forgetting to restart Claude Desktop after config changes'
            ],
            'example_usage': [
                'claude> Create a file: create("./notes.txt", content="My notes")',
                'claude> List files: list("./")',
                'claude> Edit file: edit("./notes.txt", mode="append", new_string="\\nMore notes")',
                'claude> Delete file: delete("./notes.txt")'
            ]
        }

    def _instructions_openai_chatgpt(self) -> dict:
        """Generate setup instructions for OpenAI ChatGPT (custom actions).

        Returns:
            dict: Configuration for OpenAI custom actions/plugins
        """
        return {
            'platform': 'OpenAI ChatGPT (custom actions)',
            'type': 'Web/API',
            'steps': [
                'Note: OpenAI does not yet support MCP protocol directly',
                'Alternative: Use OpenAI API with function calling (see anthropic_api section)',
                'Or create a custom GPT with webhook integration',
                'SAPÉ f-MCP must run on accessible HTTP server (not localhost)'
            ],
            'custom_gpt_approach': {
                'requirements': [
                    'Run SAPÉ f-MCP on public/accessible server',
                    'Use --transport streamable-http flag',
                    'Configure firewall to allow incoming requests on port 8089',
                    'Set up HTTPS/SSL for production use'
                ],
                'instructions': [
                    '1. Start SAPÉ f-MCP: python main.py --cli --transport streamable-http',
                    '2. Create a Custom GPT at https://chat.openai.com/gpts/editor',
                    '3. In "Configure" tab, add action with these details:',
                    '4. Authentication: "OAuth 2.0" or "API Key"',
                    '5. Schema: Define endpoint for each SAPÉ tool',
                    '6. (This requires manual API wrapper, not yet automated)'
                ]
            },
            'function_calling_api': {
                'note': 'More practical: Use OpenAI API with function calling',
                'instructions': [
                    'Use OpenAI Python library with tool definitions',
                    'Call SAPÉ f-MCP from your application code',
                    'Example: openai.ChatCompletion.create(model="gpt-4", tools=[...], messages=[...])',
                    'See "generic_llms" section for implementation pattern'
                ]
            },
            'common_pitfalls': [
                'MCP protocol not supported by OpenAI yet (standard API required)',
                'Localhost not accessible from OpenAI (need public server)',
                'SSL/HTTPS required for production (not self-signed certs)',
                'CORS issues when calling from browser (use API, not frontend)',
                'Rate limiting on SAPÉ server if high volume'
            ]
        }

    def _instructions_anthropic_api(self) -> dict:
        """Generate setup instructions for Anthropic API (direct integration).

        Returns:
            dict: Configuration for Anthropic SDK / API
        """
        return {
            'platform': 'Anthropic API / Claude API',
            'type': 'Programmatic',
            'intro': 'Use Claude API directly with MCP tools for tool calling',
            'setup': {
                'requirements': [
                    'Anthropic Python SDK: pip install anthropic',
                    'API key from https://console.anthropic.com',
                    'SAPÉ f-MCP running (local or remote)'
                ]
            },
            'code_example': '''
import json
from anthropic import Anthropic
import subprocess

# Start SAPÉ f-MCP server
server_process = subprocess.Popen(["python", "main.py", "--cli"])

# Initialize Anthropic client
client = Anthropic()

# Define MCP tools for Claude
tools = [
    {
        "name": "create",
        "description": "Create a new file or directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "is_dir": {"type": "boolean"},
                "content": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    # ... include other tools (see tools list above) ...
]

# Example conversation
messages = [
    {"role": "user", "content": "Create a file at ./hello.txt with content \\"Hello, World!\\""}
]

# Call Claude with tools
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=tools,
    messages=messages
)

# Handle tool use (implement actual tool execution)
while response.stop_reason == "tool_use":
    # Extract tool call
    tool_use = next(b for b in response.content if b.type == "tool_use")

    # Execute SAPÉ tool (via stdio or HTTP)
    # result = execute_sape_tool(tool_use.name, tool_use.input)

    # Continue conversation
    messages.append({"role": "assistant", "content": response.content})
    messages.append({"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_use.id, "content": str(result)}
    ]})

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=tools,
        messages=messages
    )
''',
            'key_points': [
                'Claude models: claude-3-5-sonnet, claude-3-opus, claude-3-haiku',
                'Tool definitions must match SAPÉ tool schemas',
                'Implement tool execution logic to call SAPÉ server',
                'Use agentic loop: Claude → tool call → execute → result → repeat',
                'Cache tool definitions across requests to save tokens'
            ],
            'common_pitfalls': [
                'Tool schemas not matching Claude expectations (missing "required" fields)',
                'Not handling all stop_reason values (tool_use, end_turn, max_tokens, stop_sequence)',
                'Forgetting to pass tools array in subsequent messages (tool context lost)',
                'Tool input validation errors (Claude may call with wrong params)',
                'Timeout if SAPÉ server not responding (add error handling)'
            ]
        }

    def _instructions_google_gemini(self) -> dict:
        """Generate setup instructions for Google Gemini.

        Returns:
            dict: Configuration for Google Gemini API
        """
        return {
            'platform': 'Google Gemini',
            'type': 'Programmatic',
            'intro': 'Use Google Gemini API with function calling (similar to Claude API)',
            'setup': {
                'requirements': [
                    'Google Generative AI SDK: pip install google-generativeai',
                    'API key from https://ai.google.dev',
                    'SAPÉ f-MCP running (local or remote)'
                ]
            },
            'code_example': '''
import google.generativeai as genai

# Configure API
genai.configure(api_key="your-api-key-here")

# Define SAPÉ tools for Gemini
tools = [genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="create",
            description="Create a new file or directory",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "path": genai.protos.Schema(type=genai.protos.Type.STRING),
                    "is_dir": genai.protos.Schema(type=genai.protos.Type.BOOLEAN),
                    "content": genai.protos.Schema(type=genai.protos.Type.STRING),
                },
                required=["path"]
            )
        ),
        # ... other tools ...
    ]
)]

# Create model with tools
model = genai.GenerativeModel("gemini-2.0-flash", tools=tools)

# Send message
response = model.generate_content(
    "Create a file at ./hello.txt with content \\"Hello, Gemini!\\"",
    tool_config=genai.protos.ToolConfig()
)

# Handle function calls
if response.candidates[0].content.parts[-1].function_call:
    # Execute SAPÉ tool
    function_name = response.candidates[0].content.parts[-1].function_call.name
    function_args = response.candidates[0].content.parts[-1].function_call.args
    # result = execute_sape_tool(function_name, function_args)
    # Continue conversation...
''',
            'key_differences_from_claude': [
                'Uses different proto format for tool definitions',
                'Function names must be lowercase with underscores',
                'No built-in message memory (manage conversation state manually)',
                'Tool calling is less integrated (requires more manual handling)',
                'Gemini 2.0 Flash recommended for tool use (better reasoning)'
            ],
            'common_pitfalls': [
                'Tool names not matching Gemini naming conventions (lowercase_with_underscores)',
                'Schema validation errors (proto types must match exactly)',
                'Not checking for function_call in response.candidates[0].content.parts',
                'Missing conversation history in multi-turn interactions',
                'API quota limits (cache tool definitions when possible)'
            ]
        }

    def _instructions_ollama(self) -> dict:
        """Generate setup instructions for Ollama (local models).

        Returns:
            dict: Configuration for Ollama integration
        """
        return {
            'platform': 'Ollama (local LLMs)',
            'type': 'Programmatic',
            'intro': 'Run SAPÉ f-MCP with local Ollama models (no API keys needed)',
            'setup': {
                'requirements': [
                    'Ollama installed from https://ollama.ai',
                    'Pull a model: ollama pull llama2 (or mistral, neural-chat, etc.)',
                    'Python: pip install ollama',
                    'SAPÉ f-MCP running (local on same machine)'
                ]
            },
            'code_example': '''
from ollama import Client
import json

# Connect to Ollama (default: localhost:11434)
client = Client(host="localhost:11434")

# Define tools (same as Claude API format)
tools = [
    {
        "name": "create",
        "description": "Create file/directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "is_dir": {"type": "boolean"},
                "content": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    # ... other tools ...
]

# Send message with tools
response = client.chat(
    model="llama2",  # or mistral, neural-chat, etc.
    messages=[
        {"role": "user", "content": "Create ./myfile.txt with \\"Hello\\""}
    ],
    tools=tools,
    stream=False
)

# Parse response
print(response.message.content)
if "tool_use" in response.message.content:
    # Ollama doesn't have native tool calling like Claude
    # Parse response text to extract tool calls manually
    # Or use structured output via prompt engineering
    pass
''',
            'local_only_benefits': [
                'No API keys or authentication required',
                'No rate limiting or quota concerns',
                'Data stays local (privacy)',
                'Faster iteration during development',
                'Free tier with no costs'
            ],
            'limitations': [
                'Less capable reasoning than Claude/GPT-4',
                'No native tool calling support (need prompt engineering)',
                'Slower inference on consumer hardware',
                'Requires significant disk space for models',
                'Manual response parsing for tool extraction'
            ],
            'recommended_models': {
                'llama2': 'Capable, good for reasoning, 7-70B available',
                'mistral': 'Faster, good quality, efficient',
                'neural-chat': 'Optimized for conversations',
                'openchat': 'Good balance of speed and quality',
                'dolphin-mixtral': 'Most capable open model (8x7B)',
                'note': 'Use 7B or smaller for consumer GPUs, 13-70B for high-VRAM setups'
            },
            'common_pitfalls': [
                'Expecting Claude-like tool calling (Ollama lacks this)',
                'Insufficient VRAM for larger models (7B minimum, 13B recommended)',
                'Not managing conversation context (tokens add up)',
                'Prompt engineering complex for tool extraction',
                'Slower performance with remote Ollama server'
            ]
        }

    def _instructions_generic_llms(self) -> dict:
        """Generate setup instructions for generic LLMs (adapter pattern).

        Returns:
            dict: Framework for integrating any LLM with SAPÉ
        """
        return {
            'platform': 'Generic LLMs',
            'type': 'Adapter Pattern',
            'intro': 'Template for integrating SAPÉ with any LLM (LangChain, LlamaIndex, local, etc.)',
            'adapter_pattern': {
                'concept': [
                    '1. Define SAPÉ tools as callable functions',
                    '2. Wrap LLM in adapter that maps tool calls to SAPÉ operations',
                    '3. Implement agentic loop: LLM → tools → results → repeat',
                    '4. Handle errors and retries gracefully'
                ],
                'implementation': '''
import subprocess
import json
from typing import Any, Dict, List

class SAPEAdapter:
    """Adapter for SAPÉ f-MCP with any LLM."""

    def __init__(self, llm, sape_db_path: str = "./permissions.db"):
        self.llm = llm
        self.sape_db_path = sape_db_path
        self.server_process = None
        self._start_sape_server()

    def _start_sape_server(self):
        """Start SAPÉ f-MCP server."""
        self.server_process = subprocess.Popen(
            ["python", "main.py", "--cli"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute SAPÉ tool via MCP protocol.

        Args:
            tool_name: Name of SAPÉ tool (create, delete, edit, etc.)
            **kwargs: Tool parameters

        Returns:
            str: JSON result from SAPÉ
        """
        # This would use the MCP protocol to call the tool
        # For now, simplified example:
        try:
            if tool_name == "create":
                path = kwargs.get("path")
                content = kwargs.get("content", "")
                with open(path, "w") as f:
                    f.write(content)
                return json.dumps({"success": True, "path": path})
            # ... other tools ...
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def chat(self, user_message: str, max_iterations: int = 5) -> str:
        """Chat with LLM with tool access."""
        messages = [{"role": "user", "content": user_message}]

        for iteration in range(max_iterations):
            # Get response from LLM
            response = self.llm.generate(messages)

            # Check if tool was called
            if response.has_tool_call():
                tool_name = response.tool_name
                tool_args = response.tool_args

                # Execute tool
                result = self.execute_tool(tool_name, **tool_args)

                # Add to conversation
                messages.append({"role": "assistant", "content": response.text})
                messages.append({"role": "user", "content": f"Tool result: {result}"})
            else:
                # No tool call, return final response
                return response.text

        return "Max iterations reached"

    def cleanup(self):
        """Stop SAPÉ server."""
        if self.server_process:
            self.server_process.terminate()
'''
            },
            'integration_points': [
                'Tool schema extraction: Map SAPÉ tools to LLM format',
                'Request handling: Convert LLM calls to SAPÉ operations',
                'Response mapping: Format SAPÉ results for LLM consumption',
                'Error handling: Retry logic for transient failures',
                'State management: Maintain conversation context'
            ],
            'frameworks': {
                'LangChain': {
                    'package': 'pip install langchain langchain-anthropic',
                    'pattern': 'Define Tool class, use AgentExecutor with tool descriptions'
                },
                'LlamaIndex': {
                    'package': 'pip install llama-index',
                    'pattern': 'Create custom ToolSpec with @tool decorators'
                },
                'AutoGPT': {
                    'package': 'pip install auto-gpt',
                    'pattern': 'Register SAPÉ as plugin in agent memory'
                },
                'Anthropic SDK': {
                    'package': 'pip install anthropic',
                    'pattern': 'Use tool_use messages with stop_reason handling'
                }
            },
            'common_pitfalls': [
                'Tool parameter mismatch (LLM format ≠ SAPÉ format)',
                'Not implementing retry/exponential backoff',
                'Forgetting to validate file paths (security)',
                'Memory leaks from unclosed server processes',
                'Not handling large file operations (base64 size limits)',
                'Missing permission checks before tool execution',
                'Race conditions in concurrent tool calls'
            ],
            'best_practices': [
                'Always validate and sanitize tool inputs',
                'Implement rate limiting to avoid overwhelming SAPÉ',
                'Use connection pooling for HTTP transport',
                'Log all tool calls for auditing',
                'Implement timeouts for long-running operations',
                'Test with permission-restricted paths first',
                'Cache tool schemas for performance'
            ]
        }

    def get_instructions_for_llm(self, llm_name: str) -> str:
        """Return setup instructions for a specific LLM.

        Args:
            llm_name: Name of LLM platform (claude, openai, gemini, ollama, generic)

        Returns:
            str: Formatted instructions as text
        """
        instructions_map = {
            'claude': self._instructions_claude_ai,
            'openai': self._instructions_openai_chatgpt,
            'anthropic': self._instructions_anthropic_api,
            'gemini': self._instructions_google_gemini,
            'ollama': self._instructions_ollama,
            'generic': self._instructions_generic_llms
        }

        if llm_name not in instructions_map:
            return f"Unknown LLM: {llm_name}. Available: {', '.join(instructions_map.keys())}"

        instructions = instructions_map[llm_name]()
        return self._format_instructions_as_text(instructions)

    def _format_instructions_as_text(self, instructions: dict) -> str:
        """Format instructions dictionary as readable text.

        Args:
            instructions: Dictionary of instructions

        Returns:
            str: Formatted text instructions
        """
        lines = []
        lines.append(f"Platform: {instructions.get('platform', 'Unknown')}")
        lines.append(f"Type: {instructions.get('type', 'Unknown')}")
        lines.append("")

        if 'intro' in instructions:
            lines.append(instructions['intro'])
            lines.append("")

        if 'steps' in instructions:
            lines.append("Steps:")
            for i, step in enumerate(instructions['steps'], 1):
                lines.append(f"  {i}. {step}")
            lines.append("")

        if 'code_example' in instructions:
            lines.append("Code Example:")
            lines.append(instructions['code_example'])
            lines.append("")

        if 'common_pitfalls' in instructions:
            lines.append("Common Pitfalls:")
            for pitfall in instructions['common_pitfalls']:
                lines.append(f"  - {pitfall}")
            lines.append("")

        return "\n".join(lines)

    def client_config(self) -> dict:
        """Build the one document a client configuration file can hold verbatim.

        :meth:`generate` describes the installation — tools, permissions, setup
        notes — and is reference material: pasting it into a client would carry
        keys the client does not understand. This returns just the
        ``mcpServers`` entry, under the same name the setup wizard uses so a
        user who sees both does not register the server twice.

        Returns:
            dict: ``{"mcpServers": {"sape-f-mcp": {...}}}``

        Raises:
            ValueError: If the installation cannot be detected, in which case
                there is no command to launch and no configuration to show.
        """
        from src.mcp_config_generator import MCPConfigGenerator

        generator = MCPConfigGenerator()
        installation = generator.detect_installation()
        db_path = getattr(getattr(self.server, 'permissions', None), 'db_path', None)
        entry = generator.generate_config(installation, db_path=db_path)
        return {'mcpServers': {self.CLIENT_SERVER_NAME: entry}}

    def to_client_config_string(self, indent: int = 2) -> str:
        """Return the client configuration as pretty-printed JSON.

        Args:
            indent: JSON indentation level

        Returns:
            str: JSON that can be pasted into a client configuration file

        Raises:
            ValueError: If the installation cannot be detected.
        """
        return json.dumps(self.client_config(), indent=indent, ensure_ascii=False)

    def to_json_string(self, indent: int = 2) -> str:
        """Return pretty-printed JSON suitable for copy-paste.

        Args:
            indent: JSON indentation level

        Returns:
            str: Pretty-printed JSON string
        """
        config = self.generate()
        return json.dumps(config, indent=indent, ensure_ascii=False)

    def to_file(self, filepath: str) -> str:
        """Write configuration to JSON file.

        Args:
            filepath: Path to output file

        Returns:
            str: Path to written file
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json_string())

        return str(path)
