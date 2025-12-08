# 🗃️ Obsidian Vault Agent

An AI-powered terminal agent for analyzing and modifying files in your Obsidian vault.

## Features

- **Interactive Chat Mode** - Have conversations about your notes with Claude AI
- **File Analysis** - Analyze content, find patterns, suggest improvements
- **File Modification** - Create, update, and organize notes based on prompts
- **Search & Browse** - Search content, list files, view vault structure
- **Smart Context** - The AI understands markdown, links, tags, and Obsidian conventions

## Installation

### 1. Clone and install dependencies

```bash
cd obsidian-agent

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project directory:

```bash
# Your Anthropic API key (get one at https://console.anthropic.com)
ANTHROPIC_API_KEY=your-api-key-here

# Path to your Obsidian vault
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault
```

Or pass these as command-line arguments.

## Usage

### Interactive Chat Mode

Start an interactive session where you can have a conversation with the AI about your vault:

```bash
python main.py chat
```

Or with explicit paths:

```bash
python main.py chat --vault ~/Documents/MyVault --api-key sk-ant-xxx
```

### Single Query Mode

Send a single prompt and get a response:

```bash
python main.py ask "List all my project notes and summarize them"
```

### Utility Commands

```bash
# Show vault structure
python main.py tree

# List all files
python main.py files

# List files matching a pattern
python main.py files --pattern "projects/*.md"

# Search for content
python main.py search "machine learning"
```

## Interactive Commands

While in chat mode, you can use these commands:

| Command | Description |
|---------|-------------|
| `/tree` | Show vault folder structure |
| `/files` | List all markdown files |
| `/reset` | Clear conversation history |
| `/quit` | Exit the agent |

## Example Prompts

Here are some things you can ask the agent to do:

### Analysis
- "Give me an overview of what's in my vault"
- "Find all notes that mention 'project X' and summarize them"
- "What topics do I write about most?"
- "Find notes that could be linked together"

### Organization
- "Create a table of contents for my projects folder"
- "Suggest tags for my untagged notes"
- "Find duplicate or similar notes"

### Modification
- "Add a summary section to the top of my meeting notes"
- "Create a new note about [topic] based on my existing notes"
- "Update all my daily notes to include a gratitude section"
- "Rename and reorganize my book notes"

### Templates
- "Create a template for weekly reviews"
- "Generate a project note structure for a new project"

## Architecture

```
obsidian-agent/
├── main.py           # Entry point
├── src/
│   ├── cli.py        # Command-line interface (Click + Rich)
│   ├── agent.py      # AI agent with tool-use capabilities
│   └── vault.py      # Vault file operations
├── requirements.txt  # Dependencies
└── pyproject.toml    # Package configuration
```

## How It Works

The agent uses Claude's tool-use capabilities to interact with your vault:

1. You send a prompt describing what you want to do
2. Claude analyzes your request and decides which tools to use
3. The agent executes file operations (read, write, search, list)
4. Claude processes the results and formulates a response
5. If needed, Claude may use multiple tools in sequence to complete complex tasks

The agent maintains conversation context, so you can have multi-turn conversations and refer back to previous responses.

## Security Notes

- Your vault contents are sent to Anthropic's API for processing
- API keys should be kept secure and never committed to version control
- The agent can modify files - always review changes in Obsidian

## License

MIT

