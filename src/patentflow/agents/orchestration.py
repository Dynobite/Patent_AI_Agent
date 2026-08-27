from typing import List
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.agents.base_agent import BaseAgent

def create_orchestration_pipeline(model, source_agents: List[BaseAgent], analysis_agent: BaseAgent) -> BaseAgent:
    """
    Creates a lean, quota-optimized orchestration pipeline using ADK.
    Executes search agents sequentially, then passes gathered data directly to AnalysisAgent.
    """
    sequential_pipeline = SequentialAgent(
        name="PatentResearchPipeline",
        description="Coordinates sequential patent search, web research, and landscape analysis.",
        sub_agents=source_agents + [analysis_agent]
    )

    return sequential_pipeline
