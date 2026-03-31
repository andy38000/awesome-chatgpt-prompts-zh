# Claude Code - Reconstructed

A functional reconstruction of the Claude Code CLI, based on architecture analysis of `@anthropic-ai/claude-code` v2.1.88.

This project recreates the core architecture of the original tool — **React/Ink terminal UI**, **command system**, **tool execution framework**, and **Anthropic API integration with tool_use loop** — as a fully working, compilable, and runnable TypeScript application.

## Architecture Overview

The original Claude Code is built with a fascinating stack:

- **React + Ink** for terminal UI rendering (yes, React components in the terminal)
- **QueryEngine** as the core conversation loop: send user message → stream AI response → execute tool calls → feed results back → repeat
- **Tool system** with `BashTool`, `FileReadTool`, `FileEditTool`, `GlobTool`, `GrepTool`, etc.
- **Command system** for slash commands (`/help`, `/model`, `/cost`, `/compact`, `/config`)
- **Cost tracking** with per-model token pricing

```
src/
├── entrypoints/
│   ├── cli.tsx              # CLI entry point (commander.js + Ink render)
│   └── nonInteractive.ts    # One-shot prompt mode (--prompt / --print)
├── components/
│   ├── App.tsx              # Root React component
│   ├── Logo.tsx             # Startup banner
│   ├── MessageView.tsx      # Message rendering (user/assistant/system)
│   ├── StatusLine.tsx       # Bottom status bar (model, tokens, cost)
│   ├── Spinner.tsx          # Animated loading spinner
│   └── ToolProgress.tsx     # Tool execution progress indicator
├── screens/
│   └── InteractiveScreen.tsx # Main REPL screen (input + messages + tools)
├── commands/
│   ├── index.ts             # Command registry and dispatch
│   ├── help.ts              # /help command
│   ├── clear.ts             # /clear command
│   ├── cost.ts              # /cost command
│   ├── model.ts             # /model command
│   ├── compact.ts           # /compact command
│   ├── config.ts            # /config command
│   ├── version.ts           # /version command
│   └── exit.ts              # /exit command
├── tools/
│   ├── index.ts             # Tool registry
│   ├── BashTool/            # Shell command execution
│   ├── FileReadTool/        # Read files with line numbers
│   ├── FileWriteTool/       # Write/create files
│   ├── FileEditTool/        # String-based file editing
│   ├── GlobTool/            # File pattern matching
│   ├── GrepTool/            # Code search (ripgrep + grep fallback)
│   ├── WebFetchTool/        # URL content fetching
│   └── TodoWriteTool/       # Task list management
├── services/
│   └── api/
│       ├── client.ts        # Anthropic SDK client initialization
│       └── systemPrompt.ts  # System prompt builder
├── QueryEngine.ts           # Core: API call → tool_use loop → response
├── state/
│   └── AppState.ts          # Global application state
├── types/
│   ├── message.ts           # Message types (User, Assistant, System, ToolUse)
│   ├── tool.ts              # Tool definition and execution interfaces
│   └── command.ts           # Command definition interface
├── constants/
│   ├── models.ts            # Model names, pricing, display names
│   └── version.ts           # Version constant
└── utils/
    ├── cost.ts              # Cost calculation and formatting
    ├── cwd.ts               # Working directory management
    └── git.ts               # Git status/branch utilities
```

## Quick Start

### Prerequisites

- Node.js >= 18
- An Anthropic API key

### Install & Run

```bash
# Install dependencies
npm install

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run in interactive mode (React/Ink terminal UI)
npx tsx src/entrypoints/cli.tsx

# Or build and run
npm run build
node dist/entrypoints/cli.js
```

### Usage

```bash
# Interactive mode (default)
claude

# One-shot prompt
claude -p "explain this codebase"

# Choose a model
claude -m haiku
claude -m opus

# Verbose mode
claude --verbose

# Auto-approve all tool use (dangerous!)
claude --dangerously-skip-permissions
```

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands and tools |
| `/model [name]` | View or switch AI model |
| `/cost` | Show token usage and cost summary |
| `/compact` | Summarize conversation to reduce context |
| `/config [option]` | View or modify configuration |
| `/clear` | Clear conversation history |
| `/version` | Show version |
| `/exit` | Exit Claude Code |

## How It Works

### The QueryEngine Loop

The core of Claude Code is the `QueryEngine` class. Here's the simplified flow:

```
User Input
    ↓
Build System Prompt (tools, git context, etc.)
    ↓
Send to Anthropic API (streaming)
    ↓
┌─→ Receive Response
│       ↓
│   Has tool_use blocks?
│       │
│     Yes → Execute each tool (BashTool, FileReadTool, etc.)
│       │       ↓
│       │   Collect tool results
│       │       ↓
│       └── Send results back to API ──────┐
│                                          │
│   No → Return final text response        │
│       ↓                                  │
│   Update cost tracking                   │
│       ↓                                  │
    Display to user
```

### Tool System

Each tool implements a `ToolDefinition` interface:
- `name`: Tool identifier sent to the API
- `description`: Sent to Claude to understand the tool's purpose
- `inputSchema`: JSON Schema for the tool's parameters
- `execute()`: Async function that performs the actual work

Tools are registered in `tools/index.ts` and converted to Anthropic API format.

## Differences from Original

This is a clean-room reconstruction, not a copy. Key simplifications:

| Feature | Original | This Version |
|---------|----------|-------------|
| Build system | Bun bundler with `feature()` macros | Standard TypeScript + tsx |
| React runtime | React compiler (auto-memoization) | Standard React 18 |
| MCP support | Full Model Context Protocol | Not included |
| Agent/Task tools | Sub-agent spawning, worktrees | Not included |
| Auth | OAuth flow, API key management | Simple env var |
| Plugins | Plugin loader, marketplace | Not included |
| Voice | Audio capture, speech-to-text | Not included |
| Bridge/Remote | Remote session management | Not included |
| Security | Sandbox, permissions, path validation | Simplified |

## Disclaimer

This is a research/educational project. The original Claude Code's architecture, copyright, and trademarks belong to Anthropic. This reconstruction is based on publicly visible architectural patterns and is **not** a copy of the original source code.
