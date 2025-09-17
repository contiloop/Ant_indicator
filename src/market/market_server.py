from mcp.server.fastmcp import FastMCP
from market import get_share_price
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.market.market import get_share_price_for_date

mcp = FastMCP("market_server")

@mcp.tool()
async def lookup_share_price(symbol: str) -> float:
    """This tool provides the current price of the given stock symbol.

    Args:
        symbol: the symbol of the stock
    """
    return get_share_price(symbol)

@mcp.tool()
async def lookup_historical_share_price(symbol: str, date: str) -> float:
    """This tool provides the historical price of the given stock symbol for a specific date.
    Use this for backtesting when you need stock prices from the past.

    Args:
        symbol: the symbol of the stock (e.g., "NVDA", "AAPL")
        date: the date in YYYY-MM-DD format (e.g., "2024-09-13")
    """
    return get_share_price_for_date(symbol, date)

if __name__ == "__main__":
    mcp.run(transport='stdio')