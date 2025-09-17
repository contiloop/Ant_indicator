import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

DB = "accounts.db"


with sqlite3.connect(DB) as conn:
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, account TEXT)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            datetime DATETIME,
            type TEXT,
            message TEXT
        )
    ''')
    cursor.execute('CREATE TABLE IF NOT EXISTS market (date TEXT PRIMARY KEY, data TEXT)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_prices (
            symbol TEXT,
            date TEXT,
            price REAL,
            PRIMARY KEY (symbol, date)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyzed_videos (
            video_id TEXT PRIMARY KEY,
            trader_name TEXT,
            title TEXT,
            channel_name TEXT,
            publication_date TEXT,
            analysis_date TEXT,
            us_market_relevant BOOLEAN,
            transcript_analyzed BOOLEAN,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

def write_account(name, account_dict):
    json_data = json.dumps(account_dict)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO accounts (name, account)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET account=excluded.account
        ''', (name.lower(), json_data))
        conn.commit()

def read_account(name):
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT account FROM accounts WHERE name = ?', (name.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
    
def write_log(name: str, type: str, message: str):
    """
    Write a log entry to the logs table.
    
    Args:
        name (str): The name associated with the log
        type (str): The type of log entry
        message (str): The log message
    """
    now = datetime.now().isoformat()
    
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (name, datetime, type, message)
            VALUES (?, datetime('now'), ?, ?)
        ''', (name.lower(), type, message))
        conn.commit()

def read_log(name: str, last_n=10):
    """
    Read the most recent log entries for a given name.
    
    Args:
        name (str): The name to retrieve logs for
        last_n (int): Number of most recent entries to retrieve
        
    Returns:
        list: A list of tuples containing (datetime, type, message)
    """
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT datetime, type, message FROM logs 
            WHERE name = ? 
            ORDER BY datetime DESC
            LIMIT ?
        ''', (name.lower(), last_n))
        
        return reversed(cursor.fetchall())

def write_market(date: str, data: dict) -> None:
    data_json = json.dumps(data)
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO market (date, data)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET data=excluded.data
        ''', (date, data_json))
        conn.commit()

def read_market(date: str) -> dict | None:
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM market WHERE date = ?', (date,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

def write_stock_price(symbol: str, date: str, price: float) -> None:
    """개별 종목의 특정 날짜 가격을 저장"""
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO stock_prices (symbol, date, price)
            VALUES (?, ?, ?)
            ON CONFLICT(symbol, date) DO UPDATE SET price=excluded.price
        ''', (symbol.upper(), date, price))
        conn.commit()

def read_stock_price(symbol: str, date: str) -> float | None:
    """개별 종목의 특정 날짜 가격을 조회"""
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT price FROM stock_prices WHERE symbol = ? AND date = ?',
                      (symbol.upper(), date))
        row = cursor.fetchone()
        return row[0] if row else None

def is_video_analyzed(video_id: str, trader_name: str) -> bool:
    """Check if a video has already been analyzed by a specific trader"""
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM analyzed_videos
            WHERE video_id = ? AND trader_name = ?
        ''', (video_id, trader_name))
        return cursor.fetchone() is not None

def record_analyzed_video(video_id: str, trader_name: str, title: str, channel_name: str,
                         publication_date: str, analysis_date: str, us_market_relevant: bool = False,
                         transcript_analyzed: bool = False) -> bool:
    """Record a video as analyzed to prevent re-analysis"""
    try:
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO analyzed_videos
                (video_id, trader_name, title, channel_name, publication_date,
                 analysis_date, us_market_relevant, transcript_analyzed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (video_id, trader_name, title, channel_name, publication_date,
                  analysis_date, us_market_relevant, transcript_analyzed))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error recording analyzed video: {e}")
        return False

