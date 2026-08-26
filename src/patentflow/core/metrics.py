import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

# Google ADK imports
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.plugins.base_plugin import BasePlugin

LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

@dataclass
class ToolMetrics:
    tool_name: str
    agent_name: str
    start_time: float
    end_time: float
    duration_seconds: float
    status: str  # 'success' or 'error'
    result_size: int = 0
    error_message: Optional[str] = None

@dataclass
class AgentMetrics:
    agent_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    status: str = 'in_progress'  # 'in_progress', 'success', 'error'
    tool_calls: int = 0

class MetricsCollector:
    """Collects and tracks execution metrics"""
    
    def __init__(self):
        self.pipeline_start_time = None
        self.pipeline_end_time = None
        self.tool_metrics = []
        self.agent_metrics = []
        self.logger = logging.getLogger("MetricsCollector")
        
    def start_pipeline(self):
        self.pipeline_start_time = time.time()
        self.logger.info("=" * 70)
        self.logger.info("🚀 PIPELINE EXECUTION STARTED")
        self.logger.info("=" * 70)
    
    def end_pipeline(self, success: bool = True):
        self.pipeline_end_time = time.time()
        duration = self.pipeline_end_time - self.pipeline_start_time
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.logger.info("=" * 70)
        self.logger.info(f"{status} - PIPELINE EXECUTION COMPLETED")
        self.logger.info(f"Total Duration: {duration:.2f} seconds")
        self.logger.info(f"Total Tool Calls: {len(self.tool_metrics)}")
        self.logger.info(f"Agents Tracked: {len([m for m in self.agent_metrics if m.end_time is not None])}")
        self.logger.info("=" * 70)
    
    def log_tool_execution(self, metrics: ToolMetrics):
        self.tool_metrics.append(metrics)
        status_icon = "✅" if metrics.status == "success" else "❌"
        self.logger.info(
            f"{status_icon} Tool: {metrics.tool_name} | "
            f"Agent: {metrics.agent_name} | "
            f"Duration: {metrics.duration_seconds:.2f}s | "
            f"Result Size: {metrics.result_size} chars"
        )
        if metrics.error_message:
            self.logger.error(f"   Error: {metrics.error_message}")
    
    def log_agent_start(self, agent_name: str):
        agent_metrics = AgentMetrics(
            agent_name=agent_name,
            start_time=time.time()
        )
        self.agent_metrics.append(agent_metrics)
        self.logger.info(f"🤖 Agent Started: {agent_name}")
        return agent_metrics
    
    def log_agent_end(self, agent_name: str, success: bool = True):
        for agent_metric in reversed(self.agent_metrics):
            if agent_metric.agent_name == agent_name and agent_metric.end_time is None:
                agent_metric.end_time = time.time()
                agent_metric.duration_seconds = agent_metric.end_time - agent_metric.start_time
                agent_metric.status = 'success' if success else 'error'
                status_icon = "✅" if success else "❌"
                self.logger.info(
                    f"{status_icon} Agent Completed: {agent_name} | "
                    f"Duration: {agent_metric.duration_seconds:.2f}s"
                )
                break
    
    def export_metrics(self, filepath: Optional[str] = None) -> str:
        if filepath is None:
            filepath = f"{LOGS_DIR}/metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        metrics_data = {
            "pipeline": {
                "start_time": datetime.fromtimestamp(self.pipeline_start_time).isoformat() if self.pipeline_start_time else None,
                "end_time": datetime.fromtimestamp(self.pipeline_end_time).isoformat() if self.pipeline_end_time else None,
                "duration_seconds": (self.pipeline_end_time - self.pipeline_start_time) if self.pipeline_end_time else None
            },
            "tools": [asdict(m) for m in self.tool_metrics],
            "agents": [asdict(m) for m in self.agent_metrics],
            "summary": {
                "total_tools": len(self.tool_metrics),
                "successful_tools": len([m for m in self.tool_metrics if m.status == "success"]),
                "total_agents_tracked": len(self.agent_metrics),
                "completed_agents": len([m for m in self.agent_metrics if m.end_time is not None])
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        self.logger.info(f"📊 Metrics exported to: {filepath}")
        return filepath


class ObservabilityPlugin(BasePlugin):
    """Custom plugin that tracks agent invocations and integrates with MetricsCollector."""
    
    def __init__(self, metrics_collector: MetricsCollector) -> None:
        super().__init__(name="observability_plugin")
        self.metrics = metrics_collector
        self.agent_count = 0
        self.llm_request_count = 0
        self.logger = logging.getLogger("ObservabilityPlugin")
    
    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        self.agent_count += 1
        agent_name = agent.name if hasattr(agent, 'name') else agent.__class__.__name__
        self.logger.info(f"[Plugin] Agent #{self.agent_count}: {agent_name} starting...")
        self.metrics.log_agent_start(agent_name)
    
    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        agent_name = agent.name if hasattr(agent, 'name') else agent.__class__.__name__
        self.logger.info(f"[Plugin] Agent completed: {agent_name}")
        self.metrics.log_agent_end(agent_name, success=True)
    
    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> None:
        self.llm_request_count += 1
        self.logger.debug(f"[Plugin] LLM request #{self.llm_request_count}")
    
    def get_summary(self) -> Dict[str, int]:
        return {
            "total_agent_invocations": self.agent_count,
            "total_llm_requests": self.llm_request_count,
            "completed_agents": len([m for m in self.metrics.agent_metrics if m.end_time is not None])
        }

metrics = MetricsCollector()
