import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from google.genai import types
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.plugins.logging_plugin import LoggingPlugin

# Ensure src is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from patentflow.core.metrics import metrics, ObservabilityPlugin
from patentflow.sources.uspto import create_uspto_agent
from patentflow.sources.google_web import create_google_search_agent
from patentflow.agents.analysis import create_analysis_agent
from patentflow.agents.orchestration import create_orchestration_pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)
logging.getLogger('google.genai').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def run_research(user_query: str):
    try:
        # Configuration
        load_dotenv()
        
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment or .env file.")
            return
            
        os.environ["GOOGLE_API_KEY"] = api_key

        retry_config = types.HttpRetryOptions(attempts=3, exp_base=2, initial_delay=1)
        model_3_5 = Gemini(model="gemini-3.5-flash-lite", retry_options=retry_config)
        model_3_1 = Gemini(model="gemini-3.1-flash-lite", retry_options=retry_config)

        # 1. Initialize Source Agents with different models to bypass concurrency limits
        uspto_agent = create_uspto_agent(model_3_5)
        google_agent = create_google_search_agent(model_3_1)

        # 2. Initialize Analysis Agent
        analysis_agent = create_analysis_agent(model_3_5)

        # 3. Create Orchestration Pipeline
        root_agent = create_orchestration_pipeline(
            model=model_3_5, 
            source_agents=[uspto_agent, google_agent], 
            analysis_agent=analysis_agent
        )

        # 4. Setup Observability
        observability_plugin = ObservabilityPlugin(metrics)
        runner = InMemoryRunner(
            agent=root_agent,
            plugins=[LoggingPlugin(), observability_plugin]
        )

        # 5. Execute
        metrics.start_pipeline()
        logger.info(f"📝 User Query: {user_query}")
        
        response = await runner.run_debug(user_query, verbose=True)
        
        metrics.end_pipeline(success=True)
        metrics_file = metrics.export_metrics()
        
        print("\n" + "=" * 70)
        print("✅ SUCCESS - RESEARCH COMPLETED")
        print(f"Metrics Exported: {metrics_file}")
        
        # Flush logs
        for handler in logging.getLogger().handlers:
            handler.flush()

        return response
        
    except Exception as e:
        logger.error(f"❌ Pipeline execution failed: {type(e).__name__}: {e}", exc_info=True)
        metrics.end_pipeline(success=False)
        return {"error": str(e), "status": "failed"}

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Find white spots in the R&D area of solid state EV batteries."
    asyncio.run(run_research(query))
