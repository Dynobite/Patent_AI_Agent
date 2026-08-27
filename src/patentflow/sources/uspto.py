import time
import logging
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

def create_uspto_agent(model) -> LlmAgent:
    """
    Creates a Patent Search Agent that uses Gemini's built-in Google Search tool
    specifically targeted at Google Patents (site:patents.google.com) to retrieve
    Patent Titles, Abstracts, AND Independent Claims (Claim 1).
    """
    return LlmAgent(
        name="USPTOSearchAgent",
        model=model,
        instruction="""You are a specialized Patent Search agent focused on patent structure and legal scope.

TASK:
1. Search for official patents regarding the user's query by calling `google_search`.
2. Format your search queries to target Google Patents, specifically searching for the Abstract AND Independent Claims (Claim 1).
   Examples of queries to execute:
   - `site:patents.google.com "your query terms" "Claim 1"`
   - `site:patents.google.com/patent "your query terms" "What is claimed is"`
3. For each patent identified, extract:
   - Patent / Publication Number (e.g. US11122233B2)
   - Patent Title
   - Filing / Issue Date
   - Abstract Summary
   - **Independent Claim 1 (or core scope of what is claimed)**
4. Return a structured list of the top 3-5 patents found, explicitly including the Claim 1 summary for each.

FORBIDDEN:
- Do NOT transfer control
- Do NOT provide non-patent web results (focus strictly on patents)""",
        tools=[google_search]
    )
