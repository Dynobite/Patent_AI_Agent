import time
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

def create_google_search_agent(model) -> LlmAgent:
    return LlmAgent(
        name="GoogleSearchAgent",
        model=model,
        instruction="""You are a specialized web search agent. Your ONLY job is:
    1. Use google_search to find relevant information on industry R&D and challenges.
    2. Return CONCISE results (max 300 words).
    3. Focus on key findings only.
    
    DO NOT:
    - Transfer control to other agents
    - Provide lengthy explanations
    - Ask follow-up questions
    
    Execute the search and return brief, focused results.""",
        tools=[google_search]
    )
