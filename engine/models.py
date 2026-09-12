"""
Data schemas and interfaces for Algorise Bots & Autoflow Engines.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class BotTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bot_name: str = "nexus"
    client_id: str = "default_client"
    input_payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "PENDING"

@dataclass
class BotResult:
    task_id: str
    bot_name: str
    success: bool
    data: Dict[str, Any]
    reasoning_trace: List[str]
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class AutoflowStep:
    step_id: str
    bot_name: str
    action: str
    parameters: Dict[str, Any]
    condition: Optional[str] = None  # e.g., "result.confidence > 0.85"

@dataclass
class AutoflowPipeline:
    flow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Algorise Enterprise Autoflow"
    client_id: str = "default_client"
    trigger_event: str = "webhook.incoming"
    steps: List[AutoflowStep] = field(default_factory=list)
    is_active: bool = True
