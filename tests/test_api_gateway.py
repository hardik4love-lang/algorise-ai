"""
Unit & Integration Tests for Algorise API Gateway Resilience & Distributed Tracing
"""

import io
import json
import pytest
from unittest.mock import MagicMock
from engine.api_gateway import AlgoriseAPIHandler, gateway_concurrency_gate, gateway_circuit_breaker, gateway_bulkhead
from engine.telemetry import TraceSpan

class MockAPIHandler(AlgoriseAPIHandler):
    def __init__(self, method: str, path: str, headers: dict = None, body: bytes = b""):
        self.command = method
        self.path = path
        self.headers = headers or {}
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self._response_code = None
        self._response_headers = {}

    def send_response(self, code, message=None):
        self._response_code = code

    def send_header(self, keyword, value):
        self._response_headers[keyword.lower()] = value

    def end_headers(self):
        pass

def test_api_gateway_get_root_with_traceparent():
    inbound_trace = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    handler = MockAPIHandler("GET", "/", headers={"traceparent": inbound_trace})
    handler.do_GET()

    assert handler._response_code == 200
    assert "traceparent" in handler._response_headers
    out_trace = handler._response_headers["traceparent"]
    assert out_trace.startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-")

    body = json.loads(handler.wfile.getvalue().decode('utf-8'))
    assert body["resilience_mesh"] == "ACTIVE_PHASES_1_TO_3"
    assert body["status"] == "OPERATIONAL"

def test_api_gateway_post_bot_execution():
    payload = json.dumps({
        "bot_name": "nexus_core",
        "input_payload": {"test": "data"}
    }).encode('utf-8')

    handler = MockAPIHandler(
        "POST",
        "/v1/bots/execute",
        headers={"Content-Length": str(len(payload)), "X-Algorise-Key": "fixture-key"},
        body=payload
    )
    handler.do_POST()

    assert handler._response_code == 200
    assert "traceparent" in handler._response_headers
    body = json.loads(handler.wfile.getvalue().decode('utf-8'))
    assert "Nexus" in body["bot"]
    assert body["success"] is True

def test_api_gateway_options_cors():
    handler = MockAPIHandler("OPTIONS", "/v1/bots/list")
    handler.do_OPTIONS()

    assert handler._response_code == 200
    assert handler._response_headers.get("access-control-allow-origin") == "*"
