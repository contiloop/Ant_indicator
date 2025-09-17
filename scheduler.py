#!/usr/bin/env python3
"""
유튜버 기반 멀티 에이전트 트레이딩 스케줄러
여러 유튜버를 동시에 추적하는 병렬 트레이딩 시스템
"""

import asyncio
import sys
from pathlib import Path
from typing import List
from datetime import datetime
import os
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

load_dotenv(override=True)

# 환경 설정
RUN_EVERY_N_MINUTES = int(os.getenv("RUN_EVERY_N_MINUTES", "1440"))  # 하루 = 1440분
RUN_EVEN_WHEN_MARKET_IS_CLOSED = (
    os.getenv("RUN_EVEN_WHEN_MARKET_IS_CLOSED", "false").strip().lower() == "true"
)

# 백테스팅 날짜 설정 (없으면 현재 날짜 사용)
BACKTEST_REFERENCE_DATE = os.getenv("BACKTEST_REFERENCE_DATE")  # 예: "2024-03-15"
BACKTEST_CURRENT_DATE = os.getenv("BACKTEST_CURRENT_DATE")      # 예: "2024-03-16"
BACKTEST_END_DATE = os.getenv("BACKTEST_END_DATE")              # 예: "2024-12-31"
IS_BACKTEST_MODE = BACKTEST_REFERENCE_DATE is not None

def create_youtuber_traders() -> List:
    """유튜버별 트레이더 생성"""
    try:
        from src.trading.trader import Trader
        from config.strategies import create_multi_trader_setup
        
        # 유튜버별 설정 가져오기
        setups = create_multi_trader_setup()
        traders = []
        
        for setup in setups:
            trader_name = setup["trader_name"].replace("_Trader", "_backtest")
            trader = Trader(name=trader_name, model_name="gpt-4.1-mini")
            
            # 트레이더에 유튜버 이름 직접 설정
            trader.target_youtuber = setup["youtuber"]
            
            # 계좌에 전략 설정
            from src.accounts.accounts import Account
            account = Account.get(trader_name)
            account.change_strategy(setup["strategy"])
            
            traders.append(trader)
            print(f"✅ {setup['youtuber']} 트레이더 생성: {trader_name} (타겟: {setup['youtuber']})")
        
        return traders
        
    except Exception as e:
        print(f"❌ 트레이더 생성 실패: {e}")
        return []

async def run_parallel_trading(ref_date=None, current_date=None):
    """병렬 트레이딩 실행"""
    try:
        # 시장 상태 확인은 일단 생략 (필요시 추가)
        # from market import is_market_open
        
        traders = create_youtuber_traders()
        
        if not traders:
            print("❌ 실행할 트레이더가 없습니다")
            return
        
        # 날짜 설정 (백테스팅이면 파라미터, 실시간이면 환경변수)
        ref_str = ref_date or BACKTEST_REFERENCE_DATE
        current_str = current_date or BACKTEST_CURRENT_DATE
        
        print(f"\n🚀 {len(traders)}개 유튜버 트레이더 병렬 실행 시작...")
        print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if ref_str:
            print(f"백테스팅 모드: 분석기준={ref_str}, 거래일={current_str}")
        
        # 🔥 핵심: 모든 트레이더를 병렬로 동시 실행 (백테스팅 날짜 포함)
        results = await asyncio.gather(
            *[trader.run(reference_date=ref_str, current_date=current_str) for trader in traders],
            return_exceptions=True
        )
        
        # 결과 출력
        print(f"\n📊 실행 결과:")
        for trader, result in zip(traders, results):
            if isinstance(result, Exception):
                print(f"❌ {trader.name}: {result}")
            else:
                print(f"✅ {trader.name}: 실행 완료")
        
        print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
    except Exception as e:
        print(f"❌ 병렬 트레이딩 실행 실패: {e}")

async def run_backtest():
    """백테스팅 모드 실행 (날짜를 하루씩 증가시키며 연속 실행)"""
    from datetime import datetime, timedelta
    
    if not IS_BACKTEST_MODE:
        print("❌ 백테스팅 모드가 아닙니다. BACKTEST_REFERENCE_DATE를 설정하세요.")
        return
    
    # 날짜 파싱
    ref_date = datetime.strptime(BACKTEST_REFERENCE_DATE, "%Y-%m-%d")
    current_date = datetime.strptime(BACKTEST_CURRENT_DATE, "%Y-%m-%d")
    end_date = datetime.strptime(BACKTEST_END_DATE, "%Y-%m-%d") if BACKTEST_END_DATE else current_date + timedelta(days=30)
    
    print(f"📈 백테스팅 모드 시작")
    print(f"기간: {ref_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"총 {(end_date - current_date).days + 1}일 시뮬레이션")
    print("-" * 50)
    
    day_count = 0
    while current_date <= end_date:
        day_count += 1
        print(f"\n📅 Day {day_count}: {current_date.strftime('%Y-%m-%d')} (분석 기준: {ref_date.strftime('%Y-%m-%d')})")
        
        # 현재 루프의 날짜로 트레이더 실행
        ref_str = ref_date.strftime("%Y-%m-%d")
        current_str = current_date.strftime("%Y-%m-%d")
        
        try:
            await run_parallel_trading(ref_str, current_str)
        except Exception as e:
            print(f"❌ Day {day_count} 실행 실패: {e}")
            # 실패해도 다음 날 계속 진행
            import traceback
            traceback.print_exc()
        
        # 다음 날로 이동
        ref_date += timedelta(days=1)
        current_date += timedelta(days=1)
        
        print(f"✅ Day {day_count} 완료, 다음 날로 이동...")
    
    print(f"\n🎉 백테스팅 완료! 총 {day_count}일 시뮬레이션 종료")

async def run_scheduler():
    """스케줄러 실행 (실시간 모드 - 주기적 반복)"""
    if IS_BACKTEST_MODE:
        print("🔄 백테스팅 모드 감지됨, run_backtest() 실행")
        await run_backtest()
        return
    
    print(f"🎯 유튜버 멀티 에이전트 스케줄러 시작 (실시간 모드)")
    print(f"실행 주기: {RUN_EVERY_N_MINUTES}분마다")
    print(f"시장 닫힌 때도 실행: {RUN_EVEN_WHEN_MARKET_IS_CLOSED}")
    print("-" * 50)
    
    while True:
        # 실제로는 시장 시간 체크를 해야 하지만 일단 생략
        if RUN_EVEN_WHEN_MARKET_IS_CLOSED:  # or is_market_open():
            await run_parallel_trading()
        else:
            print("📈 시장이 닫혀있어서 건너뜀")
        
        print(f"⏰ {RUN_EVERY_N_MINUTES}분 대기 중...")
        await asyncio.sleep(RUN_EVERY_N_MINUTES * 60)

async def run_once():
    """한 번만 실행 (테스트용)"""
    print("🧪 유튜버 멀티 에이전트 단일 실행")
    print("-" * 30)
    await run_parallel_trading()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="유튜버 기반 멀티 에이전트 트레이딩")
    parser.add_argument("--once", action="store_true", help="한 번만 실행 (스케줄러 없이)")
    args = parser.parse_args()
    
    try:
        if args.once:
            asyncio.run(run_once())
        else:
            asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        print("\n⛔ 사용자가 중단했습니다")
    except Exception as e:
        print(f"❌ 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()