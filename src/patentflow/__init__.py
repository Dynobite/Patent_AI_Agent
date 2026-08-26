from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from .sources.uspto import create_uspto_agent
from .sources.google_web import create_google_search_agent
from .agents.analysis import create_analysis_agent
from .agents.orchestration import create_orchestration_pipeline

import os

# Initialize models
retry_config = types.HttpRetryOptions(attempts=3, exp_base=2, initial_delay=1)
model = Gemini(model="gemini-3.5-flash-lite", retry_options=retry_config)

# Initialize Agents
uspto_agent = create_uspto_agent(model)
google_agent = create_google_search_agent(model)
analysis_agent = create_analysis_agent(model)

# Create Root Agent
root_agent = create_orchestration_pipeline(
    model=model, 
    source_agents=[uspto_agent, google_agent], 
    analysis_agent=analysis_agent
)

# Export the App object for agents-cli
app = App(
    root_agent=root_agent,
    name="patentflow", # Must match directory name per ADK scaffolding rules
)

__all__ = ["app"]
