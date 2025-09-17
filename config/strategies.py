"""
Investment Strategies Configuration
각 유튜버별 투자 전략 정의 및 관리
"""

# 유튜버별 전략 정의
YOUTUBER_STRATEGIES = {
    "슈카": {
        "name": "슈카월드 채널 분석 기반 투자",
        "description": "only 슈카월드의 영상 분석을 통한 미국 주식 투자 전략",
        "channel_keywords": ["슈카", "슈카월드", "SHUKA"],
        "channel_handle": "@syukaworld",
        "channel_name": "슈카월드"
    }
}

def get_strategy_by_youtuber(youtuber_name: str) -> dict:
    """유튜버 이름으로 전략 정보 반환"""
    return YOUTUBER_STRATEGIES.get(youtuber_name, {})

def get_strategy_name(youtuber_name: str) -> str:
    """유튜버 이름으로 전략명 반환"""
    strategy = get_strategy_by_youtuber(youtuber_name)
    return strategy.get("name", f"{youtuber_name} 기반 투자 전략")

def extract_youtuber_from_strategy(strategy_text: str) -> str:
    """전략 문자열에서 유튜버 이름 추출"""
    for youtuber, config in YOUTUBER_STRATEGIES.items():
        keywords = config["channel_keywords"]
        for keyword in keywords:
            if keyword in strategy_text:
                return youtuber
    return "Unknown"

def get_all_youtubers() -> list[str]:
    """등록된 모든 유튜버 목록 반환"""
    return list(YOUTUBER_STRATEGIES.keys())

def create_multi_trader_setup() -> list[dict]:
    """여러 유튜버별 트레이더 설정 생성"""
    setups = []
    for youtuber in get_all_youtubers():
        strategy = get_strategy_by_youtuber(youtuber)
        setup = {
            "trader_name": f"{youtuber}_Trader",
            "youtuber": youtuber,
            "strategy": strategy["name"],
            "description": strategy["description"]
        }
        setups.append(setup)
    return setups

# 사용 예시
if __name__ == "__main__":
    # 단일 전략 테스트
    print("슈카 전략:", get_strategy_name("슈카"))
    
    # 전략에서 유튜버 추출 테스트
    strategy_text = "슈카 채널 분석 기반 투자"
    youtuber = extract_youtuber_from_strategy(strategy_text)
    print(f"추출된 유튜버: {youtuber}")
    
    # 멀티 트레이더 설정
    multi_setup = create_multi_trader_setup()
    for setup in multi_setup:
        print(f"- {setup['trader_name']}: {setup['strategy']}")