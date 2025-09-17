# 🤖 Ant Indicator

A "Human Indicator" analysis system that verifies YouTuber investment performance through backtesting

## Overview

This system validates which YouTubers are truly "human indicators" by backtesting the returns from following specific YouTuber investment videos exclusively.

## Key Features

- Automated YouTube video analysis and investment recommendation extraction via MCP
- Backtesting and performance comparison of YouTuber-specific investment strategies
- 3-stage AI agent pipeline (Researcher → Analyst → Portfolio Manager)
- Duplicate video analysis prevention
- Portfolio performance tracking and "human indicator" verification

## System Architecture

```
Researcher Agent ──→ Analyst Agent ──→ Portfolio Manager
     ▲                    ▲                    ▲
     │                    │                    │
YouTube MCP         Polygon API        Accounts DB
```

### AI Agent Roles

- **Researcher**: YouTube video search, transcript analysis, investment insight extraction
- **Analyst**: Market data analysis, investment recommendation generation
- **Portfolio Manager**: Trading decisions, portfolio management, actual trade execution

## Tech Stack

- **Python 3.11+** / **UV** (Package Management)
- **OpenAI GPT-4.1-mini** (AI Model)
- **MCP (Model Control Protocol)** (Agent Communication)
- **YouTube API** / **Polygon.io API** (Data Sources)
- **SQLite** (Database)
- **OpenAI Trace Dashboard** (Monitoring)

## Installation & Usage

### 1. Environment Setup

```bash
git clone https://github.com/contiloop/Ant_indicator.git
cd ant_indicator

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### 2. API Key Configuration

Create a `.env` file and set the required API keys:

```bash
# Required API Keys
OPENAI_API_KEY=your_openai_key
YOUTUBE_MCP_API_KEY=your_youtube_mcp_key
YOUTUBE_MCP_PROFILE=your_profile
POLYGON_API_KEY=your_polygon_key

# Notifications
PUSHOVER_USER=your_pushover_user
PUSHOVER_TOKEN=your_pushover_token

# Monitoring
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=your_project_name
LANGSMITH_TRACING=true

# Account Settings
INITIAL_BALANCE=10000.0

# Backtesting (Optional)
BACKTEST_REFERENCE_DATE=2024-09-12
BACKTEST_CURRENT_DATE=2024-09-13
BACKTEST_END_DATE=2024-09-14
```

### 3. Account Initialization

```bash
uv run reset_accounts.py
```

### 4. Execution

```bash
# Single execution (test)
uv run scheduler.py --once

# Backtesting mode
uv run scheduler.py

# Real-time mode (remove backtesting dates)
uv run scheduler.py
```

## Project Structure

```
ant_indicator/
├── src/
│   ├── accounts/          # Account management
│   ├── trading/           # Trading logic
│   └── market/            # Market data
├── config/
│   ├── templates.py       # AI prompts
│   ├── strategies.py      # Investment strategies
│   └── mcp_params.py      # MCP configuration
├── memory/                # Agent memory
├── scheduler.py           # Main scheduler
├── reset_accounts.py      # Account initialization
└── accounts.db            # Database
```

## Monitoring

### Database Checks
```bash
# Account status
sqlite3 accounts.db "SELECT * FROM accounts;"

# Analysis history
sqlite3 accounts.db "SELECT * FROM analyzed_videos ORDER BY created_at DESC LIMIT 10;"
```

### OpenAI Trace Dashboard
- AI agent execution tracking
- Performance monitoring
- Error debugging

## References

- [The Complete Agentic AI Engineering Course](https://edwarddonner.com/2025/04/21/the-complete-agentic-ai-engineering-course/) - Comprehensive guide to building AI agent systems
- [YouTube MCP Toolbox](https://smithery.ai/server/@jikime/py-mcp-youtube-toolbox) - MCP server for YouTube video analysis and transcript extraction

## Disclaimer

This system is created for educational and research purposes. When using for actual investments, thorough review and risk management are required. Users are responsible for any investment losses.