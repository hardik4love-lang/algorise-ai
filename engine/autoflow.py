"""
Algorise Autoflow Engine
Proprietary event-driven automation orchestrator for multi-agent chains and conditional workflows.

Phase 1 Hardening (2026-10):
  - BotStepGuard applied per step: circuit breaker + exponential-backoff retry
  - Step-level exception isolation: one bot failure no longer terminates the pipeline
  - FAILED_PARTIAL status distinguishes degraded execution from clean completion
  - Circuit state snapshot attached to every execution response
  - Structured failure metadata captured per-step for post-mortem analysis
"""

import time
import traceback
from typing import Any, Dict, List, Optional

from .circuit_breaker import BotStepGuard, CircuitBreakerOpenError, RetryExhaustedError
from .guardrails import safety_gate
from .quarantine import dlq
from .logging import get_logger
from .tracing import get_tracer, SpanAttributes
from .models import AutoflowPipeline, AutoflowStep, BotTask, BotResult
from .bots import NexusBot, CortexBot, HunterBot, SentinelBot, PulseBot

log = get_logger(__name__)
tracer = get_tracer("algorise.autoflow")

# Step failure strategies — defined on AutoflowStep.on_failure (new optional field)
STRATEGY_ABORT   = "abort"   # Halt pipeline on this step's failure (critical steps)
STRATEGY_SKIP    = "skip"    # Log failure, skip step, continue pipeline
STRATEGY_FALLBACK = "fallback"  # Use step.fallback_data as synthetic result


class AlgoriseAutoflowEngine:
    def __init__(self):
        self.bots = {
            "nexus":    NexusBot(),
            "cortex":   CortexBot(),
            "hunter":   HunterBot(),
            "sentinel": SentinelBot(),
            "pulse":    PulseBot(),
        }
        self.pipelines: Dict[str, AutoflowPipeline] = {}

    def register_pipeline(self, pipeline: AutoflowPipeline):
        self.pipelines[pipeline.flow_id] = pipeline
        return pipeline.flow_id

    @staticmethod
    def _evaluate_condition(condition_str: str, context: Dict[str, Any]) -> bool:
        """Safely evaluates a step condition string against the flow context without code execution."""
        if not condition_str or not condition_str.strip():
            return True

        cond = condition_str.strip()

        def _lookup(token: str):
            if "." in token:
                parts = token.split(".")
                curr = context
                for p in parts:
                    if isinstance(curr, dict) and p in curr:
                        curr = curr[p]
                    else:
                        return None
                return curr
            if token in context:
                return context[token]
            trigger = context.get("trigger")
            if isinstance(trigger, dict) and token in trigger:
                return trigger[token]
            return None

        # Inverted boolean flag check, e.g. "!skip_processing"
        if cond.startswith("!"):
            var_name = cond[1:].strip()
            return not bool(_lookup(var_name))

        # Binary operators
        for op in ["==", "!=", ">=", "<=", ">", "<", " in "]:
            if op in cond:
                left_str, right_str = [p.strip() for p in cond.split(op, 1)]

                def _parse(val_token: str):
                    if (val_token.startswith("'") and val_token.endswith("'")) or \
                       (val_token.startswith('"') and val_token.endswith('"')):
                        return val_token[1:-1]
                    if val_token.lower() == "true":
                        return True
                    if val_token.lower() == "false":
                        return False
                    if val_token.lower() in ("none", "null"):
                        return None
                    try:
                        if "." in val_token and not any(c.isalpha() for c in val_token):
                            return float(val_token)
                        return int(val_token)
                    except ValueError:
                        return _lookup(val_token)

                l_val = _parse(left_str)
                r_val = _parse(right_str)

                if op == "==":
                    return l_val == r_val
                elif op == "!=":
                    return l_val != r_val
                elif op == ">=":
                    return l_val is not None and r_val is not None and l_val >= r_val
                elif op == "<=":
                    return l_val is not None and r_val is not None and l_val <= r_val
                elif op == ">":
                    return l_val is not None and r_val is not None and l_val > r_val
                elif op == "<":
                    return l_val is not None and r_val is not None and l_val < r_val
                elif op == " in ":
                    return l_val in r_val if r_val is not None else False

        # Fallback: check truthiness of variable in context
        return bool(_lookup(cond))

    def execute_flow(
        self,
        flow_id: str,
        trigger_payload: Dict[str, Any],
        resume_from_step: Optional[str] = None,  # Step ID to resume from (checkpoint recovery)
    ) -> Dict[str, Any]:
        """
        Execute a multi-step Autoflow pipeline with full fault isolation.

        Each step is wrapped by a BotStepGuard (circuit breaker + retry).
        Step failures are isolated — the pipeline continues unless the step
        declares on_failure='abort'.

        Args:
            flow_id:          Registered pipeline identifier.
            trigger_payload:  Initial context payload.
            resume_from_step: If set, skip all steps before this step_id (checkpoint resume).

        Returns:
            Execution result dict with status COMPLETED | FAILED_PARTIAL | FAILED.
        """
        if flow_id not in self.pipelines:
            raise ValueError(f"Autoflow pipeline '{flow_id}' not found in Algorise Registry.")

        pipeline   = self.pipelines[flow_id]
        start_time = time.monotonic()

        execution_log: List[str] = []
        step_results:  Dict[str, Any] = {}
        failed_steps:  List[str] = []
        context = {"trigger": trigger_payload}
        overall_status = "COMPLETED"

        flow_span = tracer.start_span(f"autoflow.{pipeline.name}")
        flow_span.set_attribute(SpanAttributes.AUTO_FLOW_ID, flow_id)
        flow_span.set_attribute(SpanAttributes.PIPELINE_ID, pipeline.flow_id)
        flow_span.set_attribute(SpanAttributes.CLIENT_ID, pipeline.client_id)

        resuming = resume_from_step is not None
        log.info(
            "autoflow_start",
            flow_id=flow_id,
            pipeline=pipeline.name,
            client_id=pipeline.client_id,
            steps=len(pipeline.steps),
            resume_from=resume_from_step,
        )

        for step in pipeline.steps:
            # --- Checkpoint resume: skip already-completed steps ---
            if resuming:
                if step.step_id != resume_from_step:
                    execution_log.append(f"[SKIP] Step '{step.step_id}' skipped (checkpoint resume).")
                    continue
                else:
                    resuming = False  # Resume point reached; execute from here

            # --- Conditional Step Evaluation ---
            if step.condition and not self._evaluate_condition(step.condition, context):
                execution_log.append(f"[SKIP] Step '{step.step_id}' skipped: condition '{step.condition}' evaluated to False.")
                log.info("autoflow_step_condition_skipped", flow_id=flow_id, step_id=step.step_id, condition=step.condition)
                continue

            bot = self.bots.get(step.bot_name)
            if not bot:
                msg = f"[WARN] Bot '{step.bot_name}' not registered. Skipping step '{step.step_id}'."
                log.warning("autoflow_bot_not_found", bot_name=step.bot_name, step_id=step.step_id)
                execution_log.append(msg)
                failed_steps.append(step.step_id)
                overall_status = "FAILED_PARTIAL"
                continue

            payload = {**step.parameters, **context}
            task    = BotTask(
                bot_name=step.bot_name,
                client_id=pipeline.client_id,
                input_payload=payload,
            )

            # --- Distributed Tracing: Step Span ---
            step_span = tracer.start_span(f"autoflow.step.{step.step_id}")
            step_span.set_attribute(SpanAttributes.BOT_NAME, step.bot_name)
            step_span.set_attribute(SpanAttributes.TASK_ID, task.task_id)
            step_span.set_attribute(SpanAttributes.AUTO_FLOW_ID, flow_id)
            step_span.set_attribute(SpanAttributes.PIPELINE_ID, pipeline.flow_id)
            step_span.set_attribute(SpanAttributes.CLIENT_ID, pipeline.client_id)

            # --- BotStepGuard: circuit breaker + retry per step ---
            guard  = BotStepGuard(bot_name=step.bot_name)
            result: Optional[BotResult] = None
            step_error: Optional[str]  = None

            # --- Pre-flight Causal Safety Gate ---
            safety_res = safety_gate.audit_detailed(step.bot_name, payload)
            if not safety_res.is_approved:
                step_error = f"SafetyGateBlocked: {safety_res.status_code} ({', '.join(safety_res.audit_flags)})"
                log.error(
                    "autoflow_step_safety_blocked",
                    flow_id=flow_id, step_id=step.step_id, bot=step.bot_name,
                    status_code=safety_res.status_code,
                )

            if step_error is None:
                try:
                    result = guard.execute(bot.execute, task)
                    if not result.success:
                        err_msg = result.data.get("error", "Bot reported unsuccessful execution") if isinstance(result.data, dict) else "Bot reported unsuccessful execution"
                        step_error = f"BotExecutionFailed: {err_msg}"
                        log.warning(
                            "autoflow_step_bot_failed",
                            flow_id=flow_id, step_id=step.step_id, bot=step.bot_name, error=err_msg,
                        )
                    else:
                        step_results[step.step_id] = {
                            "bot":        step.bot_name,
                            "status":     "ok",
                            "success":    result.success,
                            "data":       result.data,
                            "latency_ms": result.latency_ms,
                        }
                        context[step.step_id] = result.data
                        execution_log.append(
                            f"[OK] Step '{step.step_id}' · Bot '{step.bot_name}' · {result.latency_ms}ms"
                        )
                        log.info(
                            "autoflow_step_ok",
                            flow_id=flow_id,
                            step_id=step.step_id,
                            bot=step.bot_name,
                            latency_ms=result.latency_ms,
                        )
                        step_span.set_attribute(SpanAttributes.SUCCESS, True)
                        step_span.set_attribute(SpanAttributes.LATENCY_MS, result.latency_ms)
                        step_span.end()

                except CircuitBreakerOpenError as exc:
                    step_error = f"CircuitBreakerOpen: {exc}"
                    log.error(
                        "autoflow_step_circuit_open",
                        flow_id=flow_id, step_id=step.step_id, bot=step.bot_name,
                    )

                except RetryExhaustedError as exc:
                    step_error = f"RetryExhausted: {exc.last_exception}"
                    log.error(
                        "autoflow_step_retries_exhausted",
                        flow_id=flow_id, step_id=step.step_id, bot=step.bot_name,
                        last_exception=str(exc.last_exception),
                    )

                except Exception as exc:
                    step_error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
                    log.error(
                        "autoflow_step_unhandled_exception",
                        flow_id=flow_id, step_id=step.step_id, bot=step.bot_name,
                        exception=str(exc),
                    )

            # --- Step failure handling & DLQ Quarantine ---
            if step_error is not None:
                failure_strategy = getattr(step, "on_failure", STRATEGY_SKIP)
                step_results[step.step_id] = {
                    "bot":     step.bot_name,
                    "status":  "failed",
                    "error":   step_error,
                    "strategy_applied": failure_strategy,
                }
                failed_steps.append(step.step_id)
                execution_log.append(
                    f"[FAIL] Step '{step.step_id}' · {step_error[:120]} · strategy={failure_strategy}"
                )

                # Persist to Dead-Letter Queue
                dlq.quarantine(
                    task_id=f"{flow_id}_{step.step_id}_{int(time.time()*1000)}",
                    flow_id=flow_id,
                    step_id=step.step_id,
                    bot_name=step.bot_name,
                    client_id=pipeline.client_id,
                    payload=payload,
                    error=step_error,
                    stack_trace=traceback.format_exc() if "traceback" in step_error.lower() else None,
                )

                step_span.set_attribute(SpanAttributes.SUCCESS, False)
                step_span.set_attribute("error", True)
                step_span.set_attribute("error.message", str(step_error)[:256])
                step_span.end()

                if failure_strategy == STRATEGY_ABORT:
                    overall_status = "FAILED"
                    log.error(
                        "autoflow_abort_on_step_failure",
                        flow_id=flow_id, step_id=step.step_id,
                    )
                    break  # Hard abort: no further steps

                elif failure_strategy == STRATEGY_FALLBACK:
                    fallback_data = getattr(step, "fallback_data", {})
                    context[step.step_id] = fallback_data
                    execution_log.append(
                        f"[FALLBACK] Step '{step.step_id}' using fallback_data: {fallback_data}"
                    )
                    overall_status = "FAILED_PARTIAL"

                else:  # STRATEGY_SKIP (default)
                    overall_status = "FAILED_PARTIAL"
                    # context[step.step_id] intentionally omitted — downstream steps
                    # should guard against missing keys

        total_latency_ms = round((time.monotonic() - start_time) * 1000, 2)

        log.info(
            "autoflow_complete",
            flow_id=flow_id,
            status=overall_status,
            total_latency_ms=total_latency_ms,
            failed_steps=failed_steps,
        )

        flow_span.set_attribute(SpanAttributes.SUCCESS, overall_status == "COMPLETED")
        flow_span.set_attribute("autoflow.status", overall_status)
        flow_span.set_attribute(SpanAttributes.LATENCY_MS, total_latency_ms)
        flow_span.end()

        return {
            "flow_id":          flow_id,
            "pipeline_name":    pipeline.name,
            "client_id":        pipeline.client_id,
            "total_latency_ms": total_latency_ms,
            "status":           overall_status,
            "failed_steps":     failed_steps,
            "execution_log":    execution_log,
            "results":          step_results,
            "circuit_states":   BotStepGuard.get_all_circuit_states(),  # Observability snapshot
        }
