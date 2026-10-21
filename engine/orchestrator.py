"""
Algorise Multi-Agent Task Graph Orchestrator (Phase 3 Autonomous Framework)
Provides DAG-based dependency resolution, priority queue scheduling, circuit-breaker
fault isolation, tiered checkpoint persistence, and distributed OpenTelemetry tracing.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from engine.logging import get_logger
from engine.tracing import get_tracer, SpanAttributes
from engine.guardrails import safety_gate
from engine.circuit_breaker import BotStepGuard
from engine.checkpoint_manager import checkpoint_manager, PipelineCheckpoint
from engine.metrics import (
    BOT_CRASHES_TOTAL,
    CONCURRENT_BOT_EXECUTIONS,
    AUTOFLOW_EXECUTIONS_TOTAL,
    AUTOFLOW_EXECUTION_DURATION,
)

logger = get_logger(__name__)
tracer = get_tracer("algorise.orchestrator")


@dataclass
class AgentTask:
    """A discrete unit of autonomous agent execution in a Task Graph."""
    task_id: str
    task_type: str  # bot name or capability (e.g. "nexus", "restock_optimizer", "growth_engine")
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 3  # 1 = critical/immediate, 5 = background
    dependencies: List[str] = field(default_factory=list)  # task_ids that must complete first
    assigned_agent: Optional[str] = None
    status: str = "pending"  # pending | running | completed | failed | skipped
    result_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    latency_ms: float = 0.0


@dataclass
class TaskGraph:
    """Directed Acyclic Graph (DAG) of AgentTasks."""
    graph_id: str = field(default_factory=lambda: f"graph_{uuid.uuid4().hex[:12]}")
    name: str = "Algorise Multi-Agent Graph"
    tasks: Dict[str, AgentTask] = field(default_factory=dict)

    def add_task(self, task: AgentTask) -> TaskGraph:
        self.tasks[task.task_id] = task
        return self

    def validate_acyclic(self) -> bool:
        """Validates that the task graph contains no cyclic dependencies using Kahn's algorithm."""
        in_degree: Dict[str, int] = {t_id: 0 for t_id in self.tasks}
        adj: Dict[str, List[str]] = defaultdict(list)

        for t_id, task in self.tasks.items():
            for dep in task.dependencies:
                if dep in self.tasks:
                    adj[dep].append(t_id)
                    in_degree[t_id] += 1

        queue = deque([t_id for t_id, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited_count == len(self.tasks)


class MultiAgentGraphOrchestrator:
    """
    Centralized DAG orchestrator for autonomous agent teams.
    Synchronizes eCommerce growth generation with agent systems hardening.
    """

    def __init__(self, max_concurrency: int = 50):
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._bot_registry: Dict[str, Any] = {}
        self._init_registry()

    def _init_registry(self):
        """Discovers and registers available bots and engines."""
        from engine.bots import NexusBot, CortexBot, HunterBot, SentinelBot, PulseBot
        from engine.growth_engine import CatalogGrowthAgent
        from engine.restock_optimizer import RestockMarginOptimizer
        from engine.hero_registry import HeroBotRunner

        self._bot_registry = {
            "nexus": NexusBot(),
            "cortex": CortexBot(),
            "hunter": HunterBot(),
            "sentinel": SentinelBot(),
            "pulse": PulseBot(),
            "growth_engine": CatalogGrowthAgent(),
            "restock_optimizer": RestockMarginOptimizer(),
            "hero_runner": HeroBotRunner(),
        }

    def register_bot(self, name: str, bot_instance: Any):
        self._bot_registry[name] = bot_instance

    async def execute_task_graph(
        self,
        graph: TaskGraph,
        client_id: str = "default_client",
        resume_from_checkpoint: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes a TaskGraph with full DAG dependency resolution and fault isolation.
        """
        start_time = time.monotonic()
        if not graph.validate_acyclic():
            raise ValueError(f"TaskGraph '{graph.graph_id}' contains a circular dependency cycle.")

        flow_span = tracer.start_span(f"orchestrator.graph.{graph.name}")
        flow_span.set_attribute(SpanAttributes.AUTO_FLOW_ID, graph.graph_id)
        flow_span.set_attribute(SpanAttributes.CLIENT_ID, client_id)

        completed_results: Dict[str, Any] = {}
        failed_tasks: List[str] = []
        active_futures: Dict[str, asyncio.Task] = {}

        # Checkpoint recovery check
        checkpoint_key = f"orchestrator_{graph.graph_id}"
        if resume_from_checkpoint:
            saved_checkpoint = await checkpoint_manager.load_checkpoint(checkpoint_key)
            if saved_checkpoint and saved_checkpoint.context_snapshot:
                recovered_results = saved_checkpoint.context_snapshot.get("results", {})
                for t_id, res in recovered_results.items():
                    if t_id in graph.tasks:
                        graph.tasks[t_id].status = "completed"
                        graph.tasks[t_id].result_data = res
                        completed_results[t_id] = res
                logger.info(
                    "orchestrator_checkpoint_recovered",
                    graph_id=graph.graph_id,
                    recovered_tasks=len(completed_results),
                )

        logger.info(
            "orchestrator_graph_start",
            graph_id=graph.graph_id,
            name=graph.name,
            total_tasks=len(graph.tasks),
            client_id=client_id,
        )

        while True:
            # 1. Identify tasks ready to run
            ready_tasks: List[AgentTask] = []
            for t_id, task in graph.tasks.items():
                if task.status == "pending" and t_id not in active_futures:
                    deps_met = all(
                        dep in completed_results and graph.tasks[dep].status == "completed"
                        for dep in task.dependencies
                    )
                    dep_failed = any(
                        dep in graph.tasks and graph.tasks[dep].status in ("failed", "skipped")
                        for dep in task.dependencies
                    )
                    if dep_failed:
                        task.status = "skipped"
                        task.error = "UpstreamDependencyFailed"
                        logger.warning("orchestrator_task_skipped", task_id=t_id, reason="dependency_failed")
                    elif deps_met:
                        ready_tasks.append(task)

            # Sort ready tasks by priority (1=highest)
            ready_tasks.sort(key=lambda t: t.priority)

            # 2. Dispatch ready tasks
            for task in ready_tasks:
                task.status = "running"
                future = asyncio.create_task(
                    self._dispatch_task(task, completed_results, client_id, graph.graph_id)
                )
                active_futures[task.task_id] = future

            # 3. If no active tasks and no pending tasks, graph is complete
            if not active_futures:
                break

            # 4. Wait for at least one active task to complete
            done, _ = await asyncio.wait(
                active_futures.values(),
                return_when=asyncio.FIRST_COMPLETED
            )

            # Process completed tasks
            for fut in done:
                # Find corresponding task_id
                matched_id = None
                for t_id, f in list(active_futures.items()):
                    if f == fut:
                        matched_id = t_id
                        del active_futures[t_id]
                        break

                if matched_id:
                    task = graph.tasks[matched_id]
                    try:
                        success, data, err, latency = fut.result()
                        task.latency_ms = latency
                        task.completed_at = time.time()
                        if success:
                            task.status = "completed"
                            task.result_data = data
                            completed_results[matched_id] = data
                        else:
                            task.status = "failed"
                            task.error = err
                            failed_tasks.append(matched_id)
                    except Exception as e:
                        task.status = "failed"
                        task.error = str(e)
                        failed_tasks.append(matched_id)

                    # Persist checkpoint after each task completion
                    await checkpoint_manager.save_checkpoint(
                        PipelineCheckpoint(
                            flow_id=checkpoint_key,
                            execution_id=f"exec_{int(time.time()*1000)}",
                            client_id=client_id,
                            last_completed_step=matched_id,
                            next_step_id=None,
                            context_snapshot={"results": completed_results},
                            completed_steps=list(completed_results.keys()),
                        )
                    )

        total_latency = (time.monotonic() - start_time) * 1000
        overall_status = "COMPLETED" if not failed_tasks else ("FAILED_PARTIAL" if completed_results else "FAILED")

        logger.info(
            "orchestrator_graph_complete",
            graph_id=graph.graph_id,
            status=overall_status,
            completed=len(completed_results),
            failed=len(failed_tasks),
            latency_ms=round(total_latency, 2),
        )

        return {
            "graph_id": graph.graph_id,
            "status": overall_status,
            "tasks_total": len(graph.tasks),
            "tasks_completed": len(completed_results),
            "tasks_failed": len(failed_tasks),
            "failed_task_ids": failed_tasks,
            "results": completed_results,
            "latency_ms": round(total_latency, 2),
        }

    async def _dispatch_task(
        self,
        task: AgentTask,
        completed_results: Dict[str, Any],
        client_id: str,
        graph_id: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], float]:
        """Executes a single agent task with safety gate, concurrency bounds, and circuit breaker."""
        t_start = time.perf_counter()
        step_span = tracer.start_span(f"orchestrator.task.{task.task_id}")
        step_span.set_attribute(SpanAttributes.BOT_NAME, task.task_type)
        step_span.set_attribute(SpanAttributes.TASK_ID, task.task_id)
        step_span.set_attribute(SpanAttributes.AUTO_FLOW_ID, graph_id)
        step_span.set_attribute(SpanAttributes.CLIENT_ID, client_id)

        # Merge dependency results into task payload context
        injected_context: Dict[str, Any] = {}
        for dep in task.dependencies:
            if dep in completed_results:
                injected_context[dep] = completed_results[dep]

        merged_payload = {**task.payload, **injected_context}

        # 1. Pre-Flight Causal Safety Gate
        audit = safety_gate.audit_detailed(task.task_type, merged_payload)
        if not audit.is_approved:
            err = f"SafetyGateBlocked: {audit.status_code} ({', '.join(audit.audit_flags)})"
            elapsed = (time.perf_counter() - t_start) * 1000
            return False, None, err, elapsed

        sanitized_payload = audit.sanitized_payload if audit.sanitized_payload is not None else merged_payload

        # 2. Select and execute bot under concurrency semaphore
        bot = self._bot_registry.get(task.task_type)
        if not bot:
            # Check Hero 100 registry
            from engine.hero_registry import HERO_BOT_IDS_SET
            if task.task_type in HERO_BOT_IDS_SET:
                bot = self._bot_registry["hero_runner"]

        if not bot:
            elapsed = (time.perf_counter() - t_start) * 1000
            return False, None, f"BotNotRegistered: '{task.task_type}'", elapsed

        guard = BotStepGuard(bot_name=task.task_type)
        from engine.models import BotTask as BotExecutionTask

        bot_task = BotExecutionTask(
            task_id=task.task_id,
            bot_name=task.task_type,
            client_id=client_id,
            input_payload=sanitized_payload,
        )

        async with self._semaphore:
            CONCURRENT_BOT_EXECUTIONS.inc()
            try:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, guard.execute, bot.execute, bot_task)
                elapsed = (time.perf_counter() - t_start) * 1000
                if result.success:
                    return True, result.data, None, elapsed
                else:
                    err_msg = result.data.get("error", "ExecutionFailed") if isinstance(result.data, dict) else "ExecutionFailed"
                    return False, None, str(err_msg), elapsed
            except Exception as exc:
                BOT_CRASHES_TOTAL.labels(bot_name=task.task_type, error_type=type(exc).__name__).inc()
                elapsed = (time.perf_counter() - t_start) * 1000
                return False, None, f"{type(exc).__name__}: {str(exc)}", elapsed
            finally:
                CONCURRENT_BOT_EXECUTIONS.dec()


orchestrator = MultiAgentGraphOrchestrator()
