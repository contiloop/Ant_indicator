from pydantic import BaseModel
import json
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Callable, Optional
from .database import write_account, read_account, write_log

load_dotenv(override=True)

INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "10000.0"))
SPREAD = 0.002
TRADING_FEE_RATE = 0.0015  # 0.15% 수수료

# 백테스팅용 글로벌 변수
_backtest_date = None

def set_backtest_date(date_str: str) -> None:
    """백테스팅 날짜 설정"""
    global _backtest_date
    _backtest_date = date_str

def get_backtest_date() -> Optional[str]:
    """현재 백테스팅 날짜 반환 (환경변수 우선)"""
    import os
    # 환경변수 우선, 없으면 글로벌 변수
    return os.getenv("BACKTEST_DATE") or _backtest_date


# -----------------------------
# Price function injection (DI)
PriceFunction = Callable[[str], float]
_price_fn: Optional[PriceFunction] = None


def set_price_fn(fn: PriceFunction) -> None:
    """Set the function used to resolve a share price from a symbol."""
    global _price_fn
    _price_fn = fn


def _resolve_price_fn() -> PriceFunction:
    """Return the active price function, defaulting to market.get_share_price if available."""
    global _price_fn
    if _price_fn is not None:
        return _price_fn
    
    try:
        # Lazy import to avoid hard coupling at module import time
        import sys
        import os
        # Add the parent directory to the path so we can import from sibling modules
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from market.market import get_share_price, get_share_price_for_date

        def smart_price_fn(symbol: str) -> float:
            """백테스팅 모드면 날짜별 가격, 아니면 실시간 가격"""
            backtest_date = get_backtest_date()
            if backtest_date:
                print(f"📊 백테스팅 모드: {symbol} 가격을 {backtest_date} 기준으로 조회")
                price = get_share_price_for_date(symbol, backtest_date)
                print(f"📊 {symbol} @ {backtest_date}: ${price}")
                return price
            else:
                print(f"📊 실시간 모드: {symbol} 현재 가격 조회")
                return get_share_price(symbol)
        
        _price_fn = smart_price_fn
    except Exception:
        # Fallback dummy price function
        _price_fn = lambda symbol: 0.0
    return _price_fn


def calculate_trading_fee(amount: float) -> float:
    """거래 대금의 0.25% 수수료 계산"""
    return amount * TRADING_FEE_RATE


class Transaction(BaseModel):
    symbol: str
    quantity: int
    price: float
    timestamp: str
    rationale: str

    def total(self) -> float:
        return self.quantity * self.price
    
    def __repr__(self):
        return f"{abs(self.quantity)} shares of {self.symbol} at {self.price} each."


class Account(BaseModel):
    name: str
    balance: float
    strategy: str
    holdings: dict[str, int]
    transactions: list[Transaction]
    portfolio_value_time_series: list[tuple[str, float]]

    @classmethod
    def get(cls, name: str):
        fields = read_account(name.lower())
        if not fields:
            fields = {
                "name": name.lower(),
                "balance": INITIAL_BALANCE,
                "strategy": "",
                "holdings": {},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            write_account(name, fields)
        return cls(**fields)
    
    
    def save(self):
        write_account(self.name.lower(), self.model_dump())

    def reset(self, strategy: str):
        self.balance = INITIAL_BALANCE
        self.strategy = strategy
        self.holdings = {}
        self.transactions = []
        self.portfolio_value_time_series = []
        self.save()

    def deposit(self, amount: float):
        """ Deposit funds into the account. """
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance += amount
        print(f"Deposited ${amount}. New balance: ${self.balance}")
        self.save()

    def withdraw(self, amount: float):
        """ Withdraw funds from the account, ensuring it doesn't go negative. """
        if amount > self.balance:
            raise ValueError("Insufficient funds for withdrawal.")
        self.balance -= amount
        print(f"Withdrew ${amount}. New balance: ${self.balance}")
        self.save()

    def buy_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        """ Buy shares of a stock if sufficient funds are available. """
        price = _resolve_price_fn()(symbol)
        return self._execute_buy(symbol, quantity, rationale, price)
    
    def buy_shares_at_price(self, symbol: str, quantity: int, rationale: str, price: float) -> str:
        """ Buy shares at a specific price (to avoid redundant API calls). """
        return self._execute_buy(symbol, quantity, rationale, price)
    
    def _execute_buy(self, symbol: str, quantity: int, rationale: str, price: float) -> str:
        """ Internal method to execute buy with given price. """
        buy_price = price * (1 + SPREAD)
        trade_amount = buy_price * quantity
        fee = calculate_trading_fee(trade_amount)
        total_cost = trade_amount + fee
        
        if total_cost > self.balance:
            raise ValueError("Insufficient funds to buy shares.")
        elif price==0:
            raise ValueError(f"Unrecognized symbol {symbol}")
        
        # Update holdings
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Record transaction
        transaction = Transaction(symbol=symbol, quantity=quantity, price=buy_price, timestamp=timestamp, rationale=rationale)
        self.transactions.append(transaction)
        
        # Update balance
        self.balance -= total_cost
        self.save()
        write_log(self.name, "account", f"Bought {quantity} of {symbol} (fee: ${fee:.2f})")
        return "Completed. Latest details:\n" + self.report()

    def sell_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        """ Sell shares of a stock if the user has enough shares. """
        if self.holdings.get(symbol, 0) < quantity:
            raise ValueError(f"Cannot sell {quantity} shares of {symbol}. Not enough shares held.")
        
        price = _resolve_price_fn()(symbol)
        sell_price = price * (1 - SPREAD)
        trade_amount = sell_price * quantity
        fee = calculate_trading_fee(trade_amount)
        total_proceeds = trade_amount - fee
        
        # Update holdings
        self.holdings[symbol] -= quantity
        
        # If shares are completely sold, remove from holdings
        if self.holdings[symbol] == 0:
            del self.holdings[symbol]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Record transaction
        transaction = Transaction(symbol=symbol, quantity=-quantity, price=sell_price, timestamp=timestamp, rationale=rationale)  # negative quantity for sell
        self.transactions.append(transaction)

        # Update balance
        self.balance += total_proceeds
        self.save()
        write_log(self.name, "account", f"Sold {quantity} of {symbol} (fee: ${fee:.2f})")
        return "Completed. Latest details:\n" + self.report()

    def calculate_portfolio_value(self):
        """ Calculate the total value of the user's portfolio. """
        total_value = self.balance
        for symbol, quantity in self.holdings.items():
            total_value += _resolve_price_fn()(symbol) * quantity
        return total_value

    def calculate_profit_loss(self, portfolio_value: float):
        """ Calculate profit or loss from the initial spend. """
        initial_spend = sum(transaction.total() for transaction in self.transactions)
        return portfolio_value - initial_spend - self.balance

    def get_holdings(self):
        """ Report the current holdings of the user. """
        return self.holdings

    def get_profit_loss(self):
        """ Report the user's profit or loss at any point in time. """
        return self.calculate_profit_loss()

    def list_transactions(self):
        """ List all transactions made by the user. """
        return [transaction.model_dump() for transaction in self.transactions]
    
    def report(self) -> str:
        """ Return a json string representing the account.  """
        portfolio_value = self.calculate_portfolio_value()
        self.portfolio_value_time_series.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), portfolio_value))
        self.save()
        pnl = self.calculate_profit_loss(portfolio_value)
        data = self.model_dump()
        data["total_portfolio_value"] = portfolio_value
        data["total_profit_loss"] = pnl
        write_log(self.name, "account", f"Retrieved account details")
        return json.dumps(data)
    
    def get_strategy(self) -> str:
        """ Return the strategy of the account """
        write_log(self.name, "account", f"Retrieved strategy")
        return self.strategy
    
    def change_strategy(self, strategy: str) -> str:
        """ At your discretion, if you choose to, call this to change your investment strategy for the future """
        self.strategy = strategy
        self.save()
        write_log(self.name, "account", f"Changed strategy")
        return "Changed strategy"

# Example of usage:
if __name__ == "__main__":
    account = Account.get("John Doe")
    account.deposit(1000)
    account.buy_shares("AAPL", 10, "Initial purchase")
    print(account.report())


