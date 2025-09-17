from contextlib import AsyncExitStack
import json
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio, MCPServerStreamableHttp, MCPServerStreamableHttpParams

from src.accounts.accounts_client import read_accounts_resource, read_strategy_resource
from src.tracers import make_trace_id
from config.templates import (
    trader_instructions,
    analyst_message,
    portfolio_manager_message,
)
from config.mcp_params import trader_mcp_server_params, researcher_mcp_server_params
from config.strategies import extract_youtuber_from_strategy
from .models import get_model
from .researcher import get_researcher_tool

MAX_TURNS = 50


async def create_mcp_server(params):
    """Create MCP server based on type (HTTP or STDIO)."""
    if isinstance(params, dict) and params.get("type") == "http":
        http_params = MCPServerStreamableHttpParams(url=params["url"])
        return MCPServerStreamableHttp(http_params, client_session_timeout_seconds=600)
    else:
        return MCPServerStdio(params, client_session_timeout_seconds=600)


class Trader:
    def __init__(self, name: str, lastname="Trader", model_name="gpt-4o-mini"):
        self.name = name
        self.lastname = lastname
        self.agent = None
        self.model_name = model_name
        self.do_trade = True

    async def create_researcher_agent(self, researcher_mcp_servers, current_date=None) -> Agent:
        """Create the researcher agent for YouTube analysis."""
        from .researcher import get_researcher
        return await get_researcher(researcher_mcp_servers, self.model_name, current_date=current_date)
    
    async def create_analyst_agent(self, trader_mcp_servers, current_date=None) -> Agent:
        """Create the analyst agent for stock recommendations."""
        return Agent(
            name="Analyst",
            instructions="You are an Investment Analyst. Analyze market data and provide stock recommendations.",
            model=get_model(self.model_name),
            mcp_servers=trader_mcp_servers,
        )
    
    async def create_portfolio_agent(self, trader_mcp_servers, current_date=None) -> Agent:
        """Create the portfolio manager agent for trade execution."""
        return Agent(
            name="PortfolioManager", 
            instructions="You are a Portfolio Manager. Execute trades based on analyst recommendations.",
            model=get_model(self.model_name),
            mcp_servers=trader_mcp_servers,
        )

    async def get_account_report(self) -> str:
        """Get account information for the trader."""
        account = await read_accounts_resource(self.name)
        account_json = json.loads(account)
        account_json.pop("portfolio_value_time_series", None)
        return json.dumps(account_json)
    
    async def get_analyzed_videos(self) -> list:
        """Get list of previously analyzed video IDs/titles."""
        try:
            from .database import get_analyzed_videos_for_trader
            return get_analyzed_videos_for_trader(self.name)
        except:
            return []
    
    async def save_analyzed_videos(self, video_info: list):
        """Save analyzed video information."""
        try:
            from .database import save_analyzed_videos
            save_analyzed_videos(self.name, video_info, self.current_date)
        except Exception as e:
            print(f"영상 분석 기록 저장 실패: {e}")

    async def parse_and_save_analyzed_videos(self, researcher_insights: str):
        """Parse researcher insights and save analyzed video information."""
        try:
            import re
            video_info = []

            # "ANALYZED VIDEOS SUMMARY:" 섹션 찾기
            if "ANALYZED VIDEOS SUMMARY:" in researcher_insights:
                summary_section = researcher_insights.split("ANALYZED VIDEOS SUMMARY:")[1]

                # 각 비디오 항목 파싱
                video_blocks = re.findall(r'- Video ID: (.+?)\n.*?Title: (.+?)\n.*?Published: (.+?)\n', summary_section, re.DOTALL)

                for video_id, title, published in video_blocks:
                    video_info.append({
                        'id': video_id.strip(),
                        'title': title.strip(),
                        'published': published.strip()
                    })

            if video_info:
                await self.save_analyzed_videos(video_info)
                print(f"✅ {len(video_info)}개 영상 분석 정보 저장 완료")
            else:
                print("📝 분석된 영상 정보를 찾을 수 없음")

        except Exception as e:
            print(f"영상 정보 파싱 실패: {e}")

    async def run_three_stage_pipeline(self, trader_mcp_servers, researcher_mcp_servers, reference_date=None, current_date=None):
        """Run the three-stage pipeline: Researcher → Analyst → Portfolio Manager."""
        
        # 백테스팅 날짜 설정 (주가 조회용)
        if current_date:
            import os
            from src.accounts.accounts import set_backtest_date
            # current_date에서 날짜 부분만 추출 (시간 제거)
            date_only = current_date.split(' ')[0] if ' ' in current_date else current_date
            set_backtest_date(date_only)
            # MCP 서버에도 환경변수로 전달
            os.environ["BACKTEST_DATE"] = date_only
            print(f"🔄 백테스팅 주가 날짜 설정: {date_only} (환경변수 포함)")
        
        account = await self.get_account_report()
        strategy = await read_strategy_resource(self.name)
        
        # 직접 설정된 유튜버 이름 사용 (fallback으로 추출 로직)
        target_youtuber = getattr(self, 'target_youtuber', None)
        if not target_youtuber:
            target_youtuber = extract_youtuber_from_strategy(strategy)
        
        # 디버깅: 유튜버 및 백테스팅 정보 확인
        print(f"🔍 {self.name} → 타겟: {target_youtuber}, 분석기준: {reference_date}, 거래일: {current_date}")
        
        # 1단계: Researcher Agent
        print(f"📰 1단계: Researcher 실행 중...")
        
        # 이미 분석한 영상 목록 조회
        analyzed_videos = await self.get_analyzed_videos()
        analyzed_video_list = "\n".join([f"- {vid}" for vid in analyzed_videos]) if analyzed_videos else "None"
        
        researcher_agent = await self.create_researcher_agent(researcher_mcp_servers, current_date)
        researcher_msg = f"""You are a YouTube Research Specialist focusing on {target_youtuber}.
        
MISSION: Analyze YouTube videos from {target_youtuber} for investment insights.

⚠️ CRITICAL BACKTESTING CONSTRAINTS:
- Reference date: {reference_date} 
- ONLY analyze videos published BEFORE {reference_date} (not on or after)
- MANDATORY: Use "published_before": "{reference_date}T00:00:00Z" in ALL search_videos calls
- Search period: 5 DAYS before {reference_date} (use published_after parameter)
- If you find videos published on {reference_date} or later, you are using FUTURE INFORMATION
- Example: Reference date {reference_date} means NO videos from {reference_date} onwards

RESEARCH FOCUS:
- Extract investment themes, stock mentions, market outlook, and trading opportunities
- Focus on US stock market relevant content only
- Today's simulated date: {current_date} (only use info available up to this date)

SEARCH REQUIREMENTS:
- Always include published_before parameter: "{reference_date}T00:00:00Z"
- Never search without date constraints
- Verify all video publication dates before analysis

🚫 DUPLICATE VIDEO PREVENTION:
- Previously analyzed videos for {self.name}:
{analyzed_video_list}
- DO NOT analyze these videos again
- Focus on NEW videos not in the above list
- If you find a video that matches the above list, skip it and find different videos
- Prioritize fresh content that hasn't been analyzed before

Provide detailed investment insights based on your YouTube research for the Investment Analyst."""
        researcher_result = await Runner.run(researcher_agent, researcher_msg, max_turns=MAX_TURNS)
        researcher_insights = str(researcher_result) if researcher_result else "No insights provided"

        # 분석된 영상 정보 저장
        await self.parse_and_save_analyzed_videos(researcher_insights)

        # 2단계: Analyst Agent  
        print(f"🔍 2단계: Analyst 실행 중...")
        analyst_agent = await self.create_analyst_agent(trader_mcp_servers, current_date)
        analyst_msg = analyst_message(self.name, strategy, account, reference_date, current_date, target_youtuber, researcher_insights)
        analyst_result = await Runner.run(analyst_agent, analyst_msg, max_turns=MAX_TURNS)
        analyst_recommendations = str(analyst_result) if analyst_result else "No recommendations provided"
        
        # 3단계: Portfolio Manager Agent
        print(f"🎯 3단계: Portfolio Manager 실행 중...")
        portfolio_agent = await self.create_portfolio_agent(trader_mcp_servers, current_date)
        portfolio_msg = portfolio_manager_message(
            self.name, strategy, account, reference_date, current_date, 
            target_youtuber, analyst_recommendations
        )
        await Runner.run(portfolio_agent, portfolio_msg, max_turns=MAX_TURNS)

    async def run_with_mcp_servers(self):
        """Set up and run the trader with MCP servers."""
        async with AsyncExitStack() as trader_stack:
            # 트레이더 MCP 서버들 초기화
            trader_mcp_servers = []
            for i, params in enumerate(trader_mcp_server_params):
                try:
                    server = await create_mcp_server(params)
                    trader_mcp_servers.append(
                        await trader_stack.enter_async_context(server)
                    )
                    print(f"✅ 트레이더 MCP 서버 {i+1} 연결 성공")
                except Exception as e:
                    print(f"❌ 트레이더 MCP 서버 {i+1} 연결 실패: {e}")
                    # 필수 서버 실패 시에만 중단 (예: accounts_server)
                    if "accounts" in str(params).lower():
                        raise Exception(f"필수 서버 연결 실패: {e}")
            
            async with AsyncExitStack() as researcher_stack:
                # 리서쳐 MCP 서버들 초기화
                researcher_mcp_servers = []
                for i, params in enumerate(researcher_mcp_server_params(self.name)):
                    try:
                        server = await create_mcp_server(params)
                        researcher_mcp_servers.append(
                            await researcher_stack.enter_async_context(server)
                        )
                        print(f"✅ 리서쳐 MCP 서버 {i+1} 연결 성공")
                    except Exception as e:
                        print(f"❌ 리서쳐 MCP 서버 {i+1} 연결 실패: {e}")
                        # 리서쳐 서버는 일부 실패해도 계속 진행
                        continue
                
                await self.run_three_stage_pipeline(trader_mcp_servers, researcher_mcp_servers, 
                                                   self.reference_date, self.current_date)

    async def run_with_trace(self):
        """Run the trader with tracing enabled."""
        trace_name = f"{self.name}-trading" if self.do_trade else f"{self.name}-rebalancing"
        trace_id = make_trace_id(f"{self.name.lower()}")
        with trace(trace_name, trace_id=trace_id):
            await self.run_with_mcp_servers()

    async def run(self, reference_date=None, current_date=None):
        """Main run method with error handling."""
        self.reference_date = reference_date
        self.current_date = current_date
        
        try:
            await self.run_with_trace()
        except Exception as e:
            print(f"Error running trader {self.name}: {e}")
            import traceback
            traceback.print_exc()
        
        # Both analyst and portfolio manager run every time now
        # No need to toggle between modes