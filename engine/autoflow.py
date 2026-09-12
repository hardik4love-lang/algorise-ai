"""
Algorise Autoflow Engine
Proprietary event-driven automation orchestrator for multi-agent chains and conditional workflows.
"""

import time
from typing import Dict, Any, List
from .models import AutoflowPipeline, AutoflowStep, BotTask, BotResult
from .bots import NexusBot, CortexBot, HunterBot, SentinelBot, PulseBot

class AlgoriseAutoflowEngine:
    def __init__(self):
        self.bots = {
            "nexus": NexusBot(),
            "cortex": CortexBot(),
            "hunter": HunterBot(),
            "sentinel": SentinelBot(),
            "pulse": PulseBot()
        }
        self.pipelines: Dict[str, AutoflowPipeline] = {}

    def register_pipeline(self, pipeline: AutoflowPipeline):
        self.pipelines[pipeline.flow_id] = pipeline
        return pipeline.flow_id

    def execute_flow(self, flow_id: str, trigger_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes an entire multi-step Autoflow pipeline sequentially with conditional logic."""
        if flow_id not in self.pipelines:
            raise ValueError(f"Autoflow pipeline {flow_id} not found in Algorise Registry.")

        pipeline = self.pipelines[flow_id]
        start_time = time.time()
        
        execution_log = []
        step_results = {}
        context = {"trigger": trigger_payload}

        for step in pipeline.steps:
            bot = self.bots.get(step.bot_name)
            if not bot:
                execution_log.append(f"[Autoflow Warning] Bot '{step.bot_name}' not registered. Skipping step.")
                continue

            # Merge parameters with context
            payload = {**step.parameters, **context}
            task = BotTask(
                bot_name=step.bot_name,
                client_id=pipeline.client_id,
                input_payload=payload
            )

            result: BotResult = bot.execute(task)
            step_results[step.step_id] = {
                "bot": step.bot_name,
                "success": result.success,
                "data": result.data,
                "latency_ms": result.latency_ms
            }

            # Update flow context for subsequent steps
            context[step.step_id] = result.data
            execution_log.append(f"[OK] Completed step '{step.step_id}' with Bot '{step.bot_name}' in {result.latency_ms}ms")

        total_latency = round((time.time() - start_time) * 1000, 2)
        return {
            "flow_id": flow_id,
            "pipeline_name": pipeline.name,
            "client_id": pipeline.client_id,
            "total_latency_ms": total_latency,
            "status": "COMPLETED",
            "execution_log": execution_log,
            "results": step_results
        }
