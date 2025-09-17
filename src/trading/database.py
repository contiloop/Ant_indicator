import sqlite3
from datetime import datetime

DB_PATH = "accounts.db"

def get_analyzed_videos_for_trader(trader_name: str) -> list:
    """특정 트레이더가 분석한 영상 목록 조회"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT video_id, title
            FROM analyzed_videos
            WHERE trader_name = ?
            ORDER BY created_at DESC
        """, (trader_name,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [f"{video_id}: {title}" for video_id, title in results]
    except Exception as e:
        print(f"분석된 영상 조회 실패: {e}")
        return []

def save_analyzed_videos(trader_name: str, video_info: list, analyzed_date: str):
    """분석된 영상 정보 저장"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for video in video_info:
            video_id = video.get('id', 'unknown')
            video_title = video.get('title', 'Unknown Title')
            
            cursor.execute("""
                INSERT OR REPLACE INTO analyzed_videos
                (video_id, trader_name, title, channel_name, publication_date, analysis_date, us_market_relevant, transcript_analyzed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (video_id, trader_name, video_title, 'Unknown Channel', 'Unknown Date', analyzed_date, False, False))
        
        conn.commit()
        conn.close()
        print(f"✅ {len(video_info)}개 영상 분석 기록 저장")
    except Exception as e:
        print(f"영상 분석 기록 저장 실패: {e}")

def clear_analyzed_videos(trader_name: str = None):
    """분석된 영상 기록 초기화"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if trader_name:
            cursor.execute("DELETE FROM analyzed_videos WHERE trader_name = ?", (trader_name,))
            print(f"✅ {trader_name} 영상 분석 기록 초기화")
        else:
            cursor.execute("DELETE FROM analyzed_videos")
            print("✅ 모든 영상 분석 기록 초기화")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"영상 분석 기록 초기화 실패: {e}")