from agents import Agent, Tool
from .models import get_model
from config.templates import researcher_instructions, research_tool


async def get_researcher(mcp_servers, model_name, current_date=None) -> Agent:
    """Create a researcher agent with the specified model and MCP servers."""
    researcher = Agent(
        name="Researcher",
        instructions=researcher_instructions(current_date=current_date),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )
    return researcher


async def get_researcher_tool(mcp_servers, model_name, current_date=None) -> Tool:
    """Create a researcher tool from the researcher agent."""
    researcher = await get_researcher(mcp_servers, model_name, current_date=current_date)
    return researcher.as_tool(tool_name="Researcher", tool_description=research_tool())