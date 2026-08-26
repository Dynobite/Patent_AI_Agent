from typing import List
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.agents.base_agent import BaseAgent

def create_orchestration_pipeline(model, source_agents: List[BaseAgent], analysis_agent: BaseAgent) -> LlmAgent:
    """
    Creates the main orchestration pipeline using ADK.
    
    Args:
        model: The LLM model to use
        source_agents: List of agents that gather data (e.g., USPTOSearchAgent, GoogleSearchAgent)
        analysis_agent: The agent that synthesizes the final report
    """
    # 1. Sequential Execution of all sources to bypass free-tier rate limits
    search_pipeline = SequentialAgent(
        name="SourceSearchPipeline",
        sub_agents=source_agents,
        description="Executes data source searches sequentially to respect API rate limits."
    )

    # 2. Sequential Pipeline: Search -> Analyze
    sequential_pipeline = SequentialAgent(
        name="SequentialResearchPipeline",
        description="Coordinates sequential research and analysis.",
        sub_agents=[
            search_pipeline,
            analysis_agent
        ]
    )

    # 3. Root Agent
    patent_root_agent = LlmAgent(
        model=model,
        name="PatentRootAgent",
        instruction="""You are the Patent Research Coordinator. 
    Delegate the user's request to the Sequential Research Pipeline.
    Present the final analysis clearly to the user.""",
        sub_agents=[sequential_pipeline]
    )

    return patent_root_agent
