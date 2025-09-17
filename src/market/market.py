from polygon import RESTClient
from dotenv import load_dotenv
import os
import sys
from datetime import datetime
# Add parent directory to path for sibling module imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from accounts.database import write_market, read_market, write_stock_price, read_stock_price
from functools import lru_cache
from datetime import timezone

load_dotenv(override=True)

polygon_api_key = os.getenv("POLYGON_API_KEY")
polygon_plan = os.getenv("POLYGON_PLAN")

is_paid_polygon = polygon_plan == "paid"
is_realtime_polygon = polygon_plan == "realtime"


def is_market_open() -> bool:
    client = RESTClient(polygon_api_key)
    market_status = client.get_market_status()
    return market_status.market == "open"


def get_all_share_prices_polygon_eod() -> dict[str, float]:
    """With much thanks to student Reema R. for fixing the timezone issue with this!"""
    client = RESTClient(polygon_api_key)

    probe = client.get_previous_close_agg("SPY")[0]
    last_close = datetime.fromtimestamp(probe.timestamp / 1000, tz=timezone.utc).date()

    results = client.get_grouped_daily_aggs(last_close, adjusted=True, include_otc=False)
    return {result.ticker: result.close for result in results}


@lru_cache(maxsize=2)
def get_market_for_prior_date(today):
    market_data = read_market(today)
    if not market_data:
        market_data = get_all_share_prices_polygon_eod()
        write_market(today, market_data)
    return market_data


def get_share_price_polygon_eod(symbol) -> float:
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    # 먼저 캐시된 데이터 확인
    cached_price = read_stock_price(symbol, today)
    if cached_price is not None:
        return cached_price
    
    # 캐시에 없으면 API 호출
    client = RESTClient(polygon_api_key)
    result = client.get_previous_close_agg(symbol)[0]
    price = result.close
    
    # 결과를 캐시에 저장
    write_stock_price(symbol, today, price)
    
    return price


def get_share_price_polygon_min(symbol) -> float:
    client = RESTClient(polygon_api_key)
    result = client.get_snapshot_ticker("stocks", symbol)
    return result.min.close or result.prev_day.close


def get_share_price_polygon(symbol) -> float:
    if is_paid_polygon:
        return get_share_price_polygon_min(symbol)
    else:
        return get_share_price_polygon_eod(symbol)


def get_share_price_for_date(symbol: str, date: str) -> float:
    """백테스팅용 특정 날짜의 주가 조회"""
    if polygon_api_key:
        try:
            # 먼저 캐시에서 확인
            cached_price = read_stock_price(symbol, date)
            if cached_price is not None:
                return cached_price
                
            # Polygon API로 특정 날짜 주가 조회
            client = RESTClient(polygon_api_key)
            result = client.get_daily_open_close_agg(symbol, date)
            price = result.close
            
            # 캐시에 저장
            write_stock_price(symbol, date, price)
            return price
            
        except Exception as e:
            print(f"특정 날짜 주가 조회 실패 ({symbol}, {date}): {e}")
            return 0.0
    return 0.0

def get_share_price(symbol) -> float:
    """현재 주가 조회 (실시간/EOD)"""
    if polygon_api_key:
        try:
            return get_share_price_polygon_eod(symbol)
        except Exception as e:
            print(f"Was not able to use the polygon API due to {e}; returning 0")
            return 0.0
    return 0.0
