import time
import logging
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

def create_uspto_agent(model) -> LlmAgent:
    """
    Creates a Patent Search Agent that uses Gemini's built-in Google Search tool
    specifically targeted at Google Patents (site:patents.google.com).
    
    This requires ZERO external API keys or complex USPTO authentication!
    """
    return LlmAgent(
        name="USPTOSearchAgent",
        model=model,
        instruction="""You are a specialized Patent Search agent.

TASK:
1. Search for official patents regarding the user's query by calling `google_search`.
2. Format your search query to target Google Patents, for example:
   `site:patents.google.com "your query terms"` or `site:patents.google.com/patent "your query terms"`
3. Retrieve patent numbers, titles, filing dates, and abstracts from the search results.
4. Return a structured list of the top 3-5 patents found.

FORBIDDEN:
- Do NOT transfer control
- Do NOT provide non-patent web results (focus strictly on patents)""",
        tools=[google_search]
    )
