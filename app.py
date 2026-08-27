import os
import sys
import asyncio
import streamlit as st
from dotenv import load_dotenv

# Ensure src is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from patentflow.core.metrics import metrics, ObservabilityPlugin
from patentflow.sources.uspto import create_uspto_agent
from patentflow.sources.google_web import create_google_search_agent
from patentflow.agents.analysis import create_analysis_agent
from patentflow.agents.orchestration import create_orchestration_pipeline

from google.genai import types
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner

# Set page config
st.set_page_config(page_title="PatentFlow AI MVP", page_icon="💡", layout="wide")

st.title("💡 PatentFlow AI")
st.markdown("### Discover White Spots in R&D and Patent Landscapes")

def init_runner():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("API Key not found in environment or .env file.")
        return None

    os.environ["GOOGLE_API_KEY"] = api_key
    # Configure aggressive HTTP retry options to handle Gemini Free Tier 429 rate limits seamlessly
    retry_config = types.HttpRetryOptions(attempts=10, exp_base=2, initial_delay=10)
    
    # Initialize Models
    model = Gemini(model="gemini-3.5-flash-lite", retry_options=retry_config)

    # Setup Agents
    uspto_agent = create_uspto_agent(model)
    google_agent = create_google_search_agent(model)
    analysis_agent = create_analysis_agent(model)

    root_agent = create_orchestration_pipeline(
        model=model,
        source_agents=[uspto_agent, google_agent],
        analysis_agent=analysis_agent
    )
    
    observability_plugin = ObservabilityPlugin(metrics)
    runner = InMemoryRunner(
        agent=root_agent,
        plugins=[observability_plugin]
    )
    return runner

import logging

class StreamlitLogHandler(logging.Handler):
    def __init__(self, log_placeholder):
        super().__init__()
        self.log_placeholder = log_placeholder
        self.logs = []
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.logs.append(msg)
            # Only keep the last 20 logs to avoid overwhelming the UI
            display_text = "\n".join(self.logs[-20:])
            self.log_placeholder.code(display_text, language="log")
        except Exception:
            self.handleError(record)

# Input form
query = st.text_input("Enter your research topic:", placeholder="e.g., solid state batteries for EVs")
log_container = st.empty()

if st.button("Start Analysis"):
    if not query:
        st.warning("Please enter a research topic.")
    else:
        # Set up UI logging
        log_handler = StreamlitLogHandler(log_container)
        log_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'))
        logging.getLogger().addHandler(log_handler)
        
        runner = init_runner()
        if runner:
            with st.spinner("Executing Research Pipeline (USPTO -> Web -> Analysis)..."):
                try:
                    # Streamlit doesn't support async easily out of the box without asyncio.run
                    # So we use an async wrapper
                    async def run_pipeline():
                        metrics.start_pipeline()
                        response = await runner.run_debug(query, verbose=False)
                        metrics.end_pipeline(success=True)
                        return response
                    
                    response = asyncio.run(run_pipeline())
                    
                    st.success("Analysis Complete!")
                    st.markdown("### Final Report")
                    
                    if hasattr(response, 'final_response') and response.final_response:
                        st.markdown(response.final_response.text)
                    else:
                        st.markdown(str(response))
                        
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")
