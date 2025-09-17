from mcp.server.fastmcp import FastMCP
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.accounts.accounts import Account, set_price_fn
from src.market.market import get_share_price, get_share_price_polygon_eod
from src.accounts.database import read_market, is_video_analyzed, record_analyzed_video
from datetime import datetime
import os

mcp = FastMCP("accounts_server")

# -----------------------------
# 가격 소스 설정 블럭
# 아래 중 하나로 선택해서 set_price_fn(...) 값을 지정하세요.
# 1) 실시간/스냅샷 API (기본)
def api_price(symbol: str) -> float:
    return float(get_share_price(symbol))

# 2) 전일종가(EOD)
def eod_price(symbol: str) -> float:
    return float(get_share_price_polygon_eod(symbol))

# 3) DB 캐시(해당 일자 레코드 사용)
def db_price(symbol: str) -> float:
    today = datetime.now().date().strftime("%Y-%m-%d")
    data = read_market(today) or {}
    return float(data.get(symbol, 0.0))

# 4) DB 우선 → 없으면 EOD
def db_then_eod(symbol: str) -> float:
    today = datetime.now().date().strftime("%Y-%m-%d")
    data = read_market(today) or {}
    price = data.get(symbol)
    return float(price) if price is not None else float(get_share_price_polygon_eod(symbol))

# 5) DB 우선 → 없으면 API
def db_then_api(symbol: str) -> float:
    today = datetime.now().date().strftime("%Y-%m-%d")
    data = read_market(today) or {}
    price = data.get(symbol)
    return float(price) if price is not None else float(get_share_price(symbol))

# 6) 테스트 고정값
def fixed_price(symbol: str) -> float:
    return 100.0

# --- 선택 방법 A: 주석으로 전환 ---
# set_price_fn(api_price)
# set_price_fn(eod_price)  # 백테스팅 미지원
# set_price_fn(db_price)
# set_price_fn(db_then_eod)
# set_price_fn(db_then_api)
# set_price_fn(fixed_price)

# 백테스팅 지원을 위해 백테스팅 날짜를 확인하는 가격 함수 생성
def backtest_aware_price(symbol: str) -> float:
    import os
    from src.market.market import get_share_price_for_date, get_share_price_polygon_eod
    
    # 환경변수에서 백테스팅 날짜 확인
    backtest_date = os.getenv("BACKTEST_DATE")
    if backtest_date:
        print(f"🔍 MCP 서버: {symbol} 백테스팅 가격 조회 ({backtest_date})")
        try:
            price = get_share_price_for_date(symbol, backtest_date)
            print(f"🔍 MCP 서버: {symbol} @ {backtest_date} = ${price}")
            return price
        except Exception as e:
            print(f"❌ 백테스팅 가격 조회 실패: {e}")
            return get_share_price_polygon_eod(symbol)
    else:
        print(f"🔍 MCP 서버: {symbol} 현재 가격 조회")
        return get_share_price_polygon_eod(symbol)

set_price_fn(backtest_aware_price)

@mcp.tool()
async def get_balance(name: str) -> float:
    """Get the cash balance of the given account name.

    Args:
        name: The name of the account holder
    """
    return Account.get(name).balance

@mcp.tool()
async def get_holdings(name: str) -> dict[str, int]:
    """Get the holdings of the given account name.

    Args:
        name: The name of the account holder
    """
    return Account.get(name).holdings

@mcp.tool()
async def buy_shares(name: str, symbol: str, quantity: int, rationale: str, price: float = None) -> float:
    """Buy shares of a stock.

    Args:
        name: The name of the account holder
        symbol: The symbol of the stock
        quantity: The quantity of shares to buy
        rationale: The rationale for the purchase and fit with the account's strategy
        price: Optional specific price to use (to avoid redundant API calls)
    """
    if price is not None:
        # Use provided price to avoid redundant API calls
        return Account.get(name).buy_shares_at_price(symbol, quantity, rationale, price)
    else:
        # Use default method (will call price function)
        return Account.get(name).buy_shares(symbol, quantity, rationale)


@mcp.tool()
async def sell_shares(name: str, symbol: str, quantity: int, rationale: str) -> float:
    """Sell shares of a stock.

    Args:
        name: The name of the account holder
        symbol: The symbol of the stock
        quantity: The quantity of shares to sell
        rationale: The rationale for the sale and fit with the account's strategy
    """
    return Account.get(name).sell_shares(symbol, quantity, rationale)

@mcp.tool()
async def change_strategy(name: str, strategy: str) -> str:
    """At your discretion, if you choose to, call this to change your investment strategy for the future.

    Args:
        name: The name of the account holder
        strategy: The new strategy for the account
    """
    return Account.get(name).change_strategy(strategy)

@mcp.resource("accounts://accounts_server/{name}")
async def read_account_resource(name: str) -> str:
    account = Account.get(name.lower())
    return account.report()

@mcp.tool()
async def check_video_analyzed(video_id: str, trader_name: str) -> bool:
    """Check if a video has already been analyzed by a specific trader to prevent duplicate analysis.

    Args:
        video_id: The unique ID of the video to check
        trader_name: The name of the trader/account
    """
    return is_video_analyzed(video_id, trader_name)

@mcp.tool()
async def mark_video_analyzed(video_id: str, trader_name: str, title: str, channel_name: str,
                             publication_date: str, analysis_date: str, us_market_relevant: bool = False,
                             transcript_analyzed: bool = False) -> bool:
    """Record a video as analyzed to prevent future re-analysis.

    Args:
        video_id: The unique ID of the video
        trader_name: The name of the trader/account
        title: The title of the video
        channel_name: The name of the channel
        publication_date: When the video was published (YYYY-MM-DD)
        analysis_date: When the analysis was performed (YYYY-MM-DD)
        us_market_relevant: Whether the video contained US market relevant content
        transcript_analyzed: Whether the transcript was actually read
    """
    return record_analyzed_video(video_id, trader_name, title, channel_name,
                                publication_date, analysis_date, us_market_relevant, transcript_analyzed)

@mcp.resource("accounts://accounts_server/{name}")
async def read_account_resource(name: str) -> str:
    account = Account.get(name.lower())
    return account.report()

@mcp.resource("accounts://strategy/{name}")
async def read_strategy_resource(name: str) -> str:
    account = Account.get(name.lower())
    return account.get_strategy()

if __name__ == "__main__":
    mcp.run(transport='stdio')