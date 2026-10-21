"""
TraceRoot AI: Telemetry Ingestor & Stack Trace Parser
Parses OpenTelemetry crash spans and Python tracebacks into structured frame records.
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional

from .models import IncidentPayload, IncidentSeverity, StackFrame


class TelemetryIngestor:
    """
    Ingests runtime crash telemetry and isolates the culprit stack frame.
    """

    FRAME_REGEX = re.compile(
        r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\S+)\n\s*(?P<code>.+)',
        re.MULTILINE,
    )

    VENDOR_PREFIXES = (
        "site-packages",
        "dist-packages",
        "/lib/python",
        "\\lib\\python",
        "/opt/hostedtoolcache/",
        "C:\\Python",
    )

    def parse_traceback(
        self,
        raw_traceback: str,
        service_name: str = "algorise-engine",
        incident_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> IncidentPayload:
        """Parses a raw Python exception traceback string."""
        frames: List[StackFrame] = []

        for match in self.FRAME_REGEX.finditer(raw_traceback):
            f_path = match.group("file").replace("\\", "/")
            l_num = int(match.group("line"))
            fn_name = match.group("func")
            code = match.group("code").strip()

            is_internal = not any(v in f_path for v in self.VENDOR_PREFIXES)
            frames.append(
                StackFrame(
                    file_path=f_path,
                    line_number=l_num,
                    function_name=fn_name,
                    code_line=code,
                    is_internal=is_internal,
                )
            )

        # Extract Error Type and Message from the final line
        lines = [line.strip() for line in raw_traceback.strip().splitlines() if line.strip()]
        last_line = lines[-1] if lines else "Exception: Unknown failure"

        if ":" in last_line:
            err_type, err_msg = last_line.split(":", 1)
            err_type = err_type.strip()
            err_msg = err_msg.strip()
        else:
            err_type = "Exception"
            err_msg = last_line

        # Infer Severity
        if err_type in ("OperationalError", "DatabaseError", "MemoryError", "SystemExit"):
            severity = IncidentSeverity.P1_CRITICAL
        elif err_type in ("KeyError", "AttributeError", "ZeroDivisionError", "TypeError", "IndexError"):
            severity = IncidentSeverity.P2_HIGH
        else:
            severity = IncidentSeverity.P3_MEDIUM

        return IncidentPayload(
            incident_id=incident_id or f"INC-{abs(hash(raw_traceback)) % 1000000:06d}",
            service_name=service_name,
            error_type=err_type,
            error_message=err_msg,
            raw_stack_trace=raw_traceback,
            trace_id=trace_id,
            span_id=span_id,
            severity=severity,
            frames=frames,
        )

    def parse_json_payload(self, json_data: Dict) -> IncidentPayload:
        """Ingests an OpenTelemetry / Sentry webhook JSON payload."""
        # Extract error type and message directly from JSON if available
        error_type = json_data.get("error_type", "Exception")
        error_message = json_data.get("error_message", "")
        raw_traceback = json_data.get("stack_trace", json_data.get("raw_exception", ""))
        service_name = json_data.get("service_name", "algorise-service")
        incident_id = json_data.get("incident_id")
        trace_id = json_data.get("trace_id")
        span_id = json_data.get("span_id")

        # Parse traceback for frames and severity
        parsed = self.parse_traceback(
            raw_traceback=raw_traceback,
            service_name=service_name,
            incident_id=None,  # Will set after
            trace_id=trace_id,
            span_id=span_id,
        )

        # Override with JSON-provided values if available
        parsed.error_type = error_type
        parsed.error_message = error_message or parsed.error_message
        parsed.incident_id = incident_id or parsed.incident_id

        return parsed
