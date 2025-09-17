import os
from dotenv import load_dotenv
from src.market import is_paid_polygon, is_realtime_polygon

load_dotenv(override=True)

# API Keys and Environment Variables
polygon_api_key = os.getenv("POLYGON_API_KEY")
youtube_api_key = os.getenv("YOUTUBE_API_KEY")  # YouTube API 키 추가
youtube_mcp_api_key = os.getenv("YOUTUBE_MCP_API_KEY")
youtube_mcp_profile = os.getenv("YOUTUBE_MCP_PROFILE")

# The MCP server for the Trader to read Market Data
if is_paid_polygon or is_realtime_polygon:
    market_mcp = {
        "command": "uvx",
        "args": ["--from", "git+https://github.com/polygon-io/mcp_polygon@v0.1.0", "mcp_polygon"],
        "env": {"POLYGON_API_KEY": polygon_api_key},
    }
else:
    market_mcp = {"command": "uv", "args": ["run", "src/market/market_server.py"]}

# The full set of MCP servers for the trader: Accounts, Push Notification and the Market
trader_mcp_server_params = [
    {"command": "uv", "args": ["run", "src/accounts/accounts_server.py"]},
    {"command": "uv", "args": ["run", "push_server.py"]},
    market_mcp,
]

# YouTube MCP 서버 설정 (리서쳐용)
def get_youtube_mcp_url():
    """YouTube MCP 서버 URL 반환 (직접 연결용)"""
    from urllib.parse import urlencode
    base_url = "https://server.smithery.ai/@jikime/py-mcp-youtube-toolbox/mcp"
    params = {
        "api_key": youtube_mcp_api_key, 
        "profile": youtube_mcp_profile
    }
    return f"{base_url}?{urlencode(params)}"

# YouTube MCP를 HTTP 방식으로 설정 (Agent용)
youtube_mcp_http = {
    "type": "http",
    "url": get_youtube_mcp_url()
}

# The full set of MCP servers for the researcher: Fetch, YouTube and Memory
def researcher_mcp_server_params(name: str):
    return [
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        youtube_mcp_http,  # HTTP 방식 YouTube MCP
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
    ]