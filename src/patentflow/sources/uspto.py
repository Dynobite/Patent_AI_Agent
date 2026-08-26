import time
import json
import logging
import httpx
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from ..core.metrics import metrics, ToolMetrics

def search_uspto_patents(query: str) -> dict:
    """
    Retrieves structured patent data from the USPTO PatentsView API.
    Instrumented with logging and metrics.
    
    Args:
        query: The search keywords for the patent abstract or title.
        
    Returns:
        Dictionary containing patent results with metadata.
    """
    tool_logger = logging.getLogger("USPTOTool")
    start_time = time.time()
    
    tool_logger.info(f"🔍 Searching USPTO patents for: '{query[:60]}...'")
    
    # We will construct a simple query using the _text_any field which searches title and abstract.
    # A more advanced version would parse the query or allow the agent to pass structured JSON.
    try:
        url = "https://api.patentsview.org/patents/query"
        # Search anywhere in text -> restricting to patent_title only
        query_json = {"_text_any": {"patent_title": query}}
        
        # We want to retrieve a few fields
        fields = ["patent_number", "patent_title", "patent_abstract", "patent_date"]
        
        params = {
            "q": json.dumps(query_json),
            "f": json.dumps(fields),
            "o": json.dumps({"per_page": 5}) # Get top 5 matches
        }
        
        response = httpx.get(url, params=params, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        patents = data.get("patents", [])
        if not patents:
            result = {"status": "success", "query": query, "result_count": 0, "results": []}
        else:
            formatted_results = []
            for p in patents:
                formatted_results.append({
                    "id": p.get("patent_number"),
                    "title": p.get("patent_title"),
                    "abstract": p.get("patent_abstract"),
                    "year": p.get("patent_date", "").split("-")[0] if p.get("patent_date") else ""
                })
                
            result = {
                "status": "success",
                "query": query,
                "result_count": len(formatted_results),
                "results": formatted_results
            }
            
        result_size = len(json.dumps(result))
        tool_logger.info(f"✅ Found {result['result_count']} patents for query: '{query[:40]}...'")
        
        # Log metrics
        duration = time.time() - start_time
        metrics.log_tool_execution(ToolMetrics(
            tool_name="search_uspto_patents",
            agent_name="USPTOSearchAgent",
            start_time=start_time,
            end_time=time.time(),
            duration_seconds=duration,
            status="success",
            result_size=result_size
        ))
        
        return result
        
    except Exception as e:
        duration = time.time() - start_time
        tool_logger.error(f"❌ Patent search failed: {e}", exc_info=True)
        
        metrics.log_tool_execution(ToolMetrics(
            tool_name="search_uspto_patents",
            agent_name="USPTOSearchAgent",
            start_time=start_time,
            end_time=time.time(),
            duration_seconds=duration,
            status="error",
            error_message=str(e)
        ))
        
        return {"status": "error", "message": str(e)}

USPTO_TOOL = FunctionTool(search_uspto_patents)

def create_uspto_agent(model) -> LlmAgent:
    return LlmAgent(
        name="USPTOSearchAgent",
        model=model,
        instruction="""You are a patent search executor using the USPTO PatentsView API.

CRITICAL: You must call the function 'search_uspto_patents' (exact name).

TASK:
1. Extract key search terms from the user's query (e.g., 'butterfly valves' or 'solid state battery').
2. Call: search_uspto_patents(query="your search terms"). Keep the query terms focused as it will search the patent_title field.
3. Return the raw JSON tool output immediately.

FORBIDDEN:
- Do NOT analyze results
- Do NOT transfer control

The ONLY function available is 'search_uspto_patents'.""",
        tools=[USPTO_TOOL]
    )
