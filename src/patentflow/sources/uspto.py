import time
import json
import logging
import httpx
from typing import Dict, Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from ..core.metrics import metrics, ToolMetrics

import os
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from google.adk.tools.openapi_tool.auth.auth_helpers import token_to_scheme_credential

def get_uspto_toolset():
    # Load the YAML spec file that is located in the project root
    spec_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uspto-openapi.yml")
    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"OpenAPI spec not found at {spec_path}")
        
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_str = f.read()

    # The user must add this to their .env file
    uspto_api_key = os.environ.get("USPTO_API_KEY", "MISSING_KEY")
    
    # Map the security scheme defined in the OpenAPI YAML (ApiKeyAuth -> X-API-KEY header)
    auth_scheme, auth_credential = token_to_scheme_credential(
        auth_scheme_name="ApiKeyAuth",
        auth_type="apikey",
        auth_location="header",
        auth_name="X-API-KEY",
        token=uspto_api_key
    )

    return OpenAPIToolset(
        spec_str=spec_str,
        spec_str_type="yaml",
        auth_scheme=auth_scheme,
        auth_credential=auth_credential
    )

def create_uspto_agent(model) -> LlmAgent:
    try:
        toolset = get_uspto_toolset()
        tools = [toolset]
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to load USPTO OpenAPI spec: {e}")
        tools = []

    return LlmAgent(
        name="USPTOSearchAgent",
        model=model,
        instruction="""You are a patent search executor using the USPTO Open Data Portal API.

You have access to a suite of USPTO API tools generated from an OpenAPI spec.
Your primary tool for searching is `search_patent_applications` (or similar POST search tool).

TASK:
1. Extract key search terms from the user's query (e.g., 'butterfly valves' or 'solid state battery').
2. Call the search tool with the appropriate JSON payload. You should typically search the title or abstract.
3. If the results are paginated, you may fetch more if necessary, but keep it brief.
4. Return the raw data.

FORBIDDEN:
- Do NOT analyze results
- Do NOT transfer control""",
        tools=tools
    )
