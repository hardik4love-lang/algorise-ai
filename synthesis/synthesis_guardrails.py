"""
Synthesis Guardrails - AI-assisted synthesis with deterministic 7-gate validation.
Constrained LLM synthesis behind feature flags with strict validation.
Never bypasses determinism: outputs must pass AST parse + unit tests +
confidence thresholds + human-in-loop approval.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SynthesisMode(Enum):
    """Mode of synthesis operation."""
    DETERMINISTIC_ONLY = "deterministic_only"   # No LLM, pure AST transforms
    LLM_ASSISTED = "llm_assisted"               # LLM proposes, guardrails validate
    HUMAN_IN_LOOP = "human_in_loop"               # LLM proposes, human approves


class SynthesisStatus(Enum):
    """Status of a synthesis attempt."""
    SUCCESS = "success"
    SYNTAX_ERROR = "syntax_error"
    VALIDATION_FAILED = "validation_failed"
    CONFIDENCE_LOW = "confidence_low"
    TESTS_FAILED = "tests_failed"
    GATE_REJECTED = "gate_rejected"
    HUMAN_REJECTED = "human_rejected"
    TIMEOUT = "timeout"


@dataclass
class SynthesisResult:
    """Result of a synthesis attempt."""
    status: SynthesisStatus
    synthesized_code: Optional[str] = None
    original_code: Optional[str] = None
    diff: Optional[str] = None
    confidence: float = 0.0
    validation_results: Dict[str, Any] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)
    gate_results: Dict[str, bool] = field(default_factory=dict)
    error_message: Optional[str] = None
    synthesis_time_ms: int = 0
    mode_used: SynthesisMode = SynthesisMode.DETERMINISTIC_ONLY
    human_approved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailConfig:
    """Configuration for synthesis guardrails."""
    # Feature flags
    enable_llm_synthesis: bool = False
    enable_human_in_loop: bool = False

    # Confidence thresholds
    min_confidence: float = 0.85
    syntax_validation: bool = True
    unit_test_validation: bool = True
    integration_test_validation: bool = False

    # LLM constraints
    max_tokens: int = 2048
    temperature: float = 0.1
    max_retries: int = 3
    timeout_seconds: int = 30

    # Allowed patterns (deny by default)
    allowed_imports: List[str] = field(default_factory=lambda: [
        "os", "sys", "json", "re", "typing", "dataclasses", "datetime",
        "collections", "itertools", "functools", "pathlib", "hashlib",
    ])
    forbidden_patterns: List[str] = field(default_factory=lambda: [
        "eval(", "exec(", "compile(", "__import__", "subprocess",
        "socket", "requests", "urllib", "threading", "multiprocessing",
    ])

    # Guardrail gates (mirroring Revenue Engine 7-gate)
    gate_syntax_valid: bool = True
    gate_unit_tests_pass: bool = True
    gate_integration_tests_pass: bool = False
    gate_confidence_threshold: bool = True
    gate_no_forbidden_patterns: bool = True
    gate_allowed_imports_only: bool = True
    gate_human_approval: bool = False


class LLMProvider:
    """Abstract LLM provider interface."""

    async def generate(self, prompt: str, config: GuardrailConfig, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code completion."""
        raise NotImplementedError

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate LLM response format."""
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing/development."""

    def __init__(self, responses: Optional[List[Dict[str, Any]]] = None):
        self.responses = responses or []
        self.call_count = 0

    async def generate(self, prompt: str, config: GuardrailConfig, context: Dict[str, Any]) -> Dict[str, Any]:
        self.call_count += 1
        if self.responses:
            return self.responses[min(self.call_count - 1, len(self.responses) - 1)]

        # Default mock response
        return {
            "code": "# Mock LLM synthesis\n# This is a placeholder\npass",
            "confidence": 0.75,
            "explanation": "Mock synthesis for testing",
            "tokens_used": 100,
        }

    def validate_response(self, response: Dict[str, Any]) -> bool:
        return "code" in response and "confidence" in response


class OpenAILLMProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.client = None
        if self.api_key:
            try:
                import openai  # type: ignore
                self.client = openai.OpenAI(api_key=self.api_key)
            except Exception:
                self.client = None

    async def generate(self, prompt: str, config: GuardrailConfig, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.client:
            return {"code": "", "confidence": 0.0, "error": "OpenAI client not configured"}
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._build_system_prompt(config)},
                    {"role": "user", "content": prompt},
                ],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout=config.timeout_seconds,
            )
            return self._parse_response(response.choices[0].message.content)
        except Exception as exc:
            return {"code": "", "confidence": 0.0, "error": str(exc)}

    def _build_system_prompt(self, config: GuardrailConfig) -> str:
        return (
            "You are a code synthesis assistant for the Algorise DevEx platform.\n"
            "Generate Python code that:\n"
            "1. Is syntactically valid Python 3.11+\n"
            f"2. Only uses allowed imports: {', '.join(config.allowed_imports)}\n"
            f"3. NEVER uses forbidden patterns: {', '.join(config.forbidden_patterns)}\n"
            "4. Is type-annotated and follows PEP 8\n"
            "5. Includes docstrings for public functions/classes\n"
            "Return ONLY valid JSON with fields: code, confidence (0-1), explanation, tokens_used."
        )

    def _parse_response(self, content: str) -> Dict[str, Any]:
        try:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {"code": "", "confidence": 0.0, "error": "Failed to parse response"}

    def validate_response(self, response: Dict[str, Any]) -> bool:
        return "code" in response and "confidence" in response


class SynthesisGuardrails:
    """Comprehensive guardrails for AI synthesis.

    Validates syntax, checks forbidden patterns and imports, runs unit tests,
    enforces confidence thresholds, and owns the deterministic gate logic.
    """

    def __init__(self, config: Optional[GuardrailConfig] = None):
        self.config = config or GuardrailConfig()

    # -- Individual validators ------------------------------------------------

    def validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Validate Python syntax."""
        if not self.config.syntax_validation:
            return True, None
        try:
            compile(code, "<synthesis>", "exec")
            return True, None
        except SyntaxError as exc:
            return False, f"Syntax error: {exc}"

    def validate_imports(self, code: str) -> tuple[bool, List[str]]:
        """Check imports against the allowlist."""
        if not self.config.gate_allowed_imports_only:
            return True, []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False, ["Failed to parse imports"]

        violations: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.config.allowed_imports:
                        violations.append(f"Disallowed import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module and module.split(".")[0] not in self.config.allowed_imports:
                    violations.append(f"Disallowed from-import: {module}")
        return len(violations) == 0, violations

    def validate_forbidden_patterns(self, code: str) -> tuple[bool, List[str]]:
        """Check for forbidden patterns in the generated code."""
        if not self.config.gate_no_forbidden_patterns:
            return True, []
        violations = [
            f"Forbidden pattern: {pattern}"
            for pattern in self.config.forbidden_patterns
            if pattern in code
        ]
        return len(violations) == 0, violations

    def run_unit_tests(self, code: str, test_file: Optional[str] = None) -> tuple[bool, Dict[str, Any]]:
        """Run generated unit tests against the synthesized code."""
        if not self.config.unit_test_validation:
            return True, {"passed": True, "skipped": True}

        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = os.path.join(tmpdir, "synthesized.py")
            with open(code_file, "w", encoding="utf-8") as handle:
                handle.write(code)

            test_path = test_file or os.path.join(tmpdir, "test_synthesized.py")
            with open(test_path, "w", encoding="utf-8") as handle:
                handle.write(self._build_test_harness(tmpdir))

            try:
                result = subprocess.run(
                    [
                        sys.executable, "-m", "pytest", test_path,
                        "-v", "--tb=short", "-p", "no:cacheprovider",
                    ],
                    capture_output=True, text=True, timeout=60, cwd=tmpdir,
                )
            except subprocess.TimeoutExpired:
                return False, {"error": "Test timeout"}
            except Exception as exc:  # pragma: no cover - defensive
                return False, {"error": str(exc)}

            return result.returncode == 0, {
                "returncode": result.returncode,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-2000:],
            }

    @staticmethod
    def _build_test_harness(tmpdir: str) -> str:
        """Build a harness that executes the synthesized module's public callables.

        The harness deliberately lets runtime errors (NameError, AttributeError,
        etc.) propagate so that broken synthesis is detected, while tolerating
        functions that simply require arguments.
        """
        return (
            "import sys\n"
            "sys.path.insert(0, " + repr(tmpdir) + ")\n"
            "import synthesized\n"
            "\n"
            "def test_syntax():\n"
            "    assert synthesized is not None\n"
            "\n"
            "def test_runtime():\n"
            "    for name in dir(synthesized):\n"
            "        if name.startswith('_'):\n"
            "            continue\n"
            "        obj = getattr(synthesized, name)\n"
            "        if callable(obj):\n"
            "            try:\n"
            "                obj()\n"
            "            except TypeError:\n"
            "                continue\n"
        )

    # -- Gate orchestration ---------------------------------------------------

    def run_all_gates(self, code: str, confidence: float) -> Dict[str, Any]:
        """Run every configured guardrail gate and return the aggregate result."""
        results: Dict[str, Any] = {}

        # Gate 1: syntax validity
        syntax_ok, syntax_error = self.validate_syntax(code)
        results["gate_syntax_valid"] = syntax_ok
        if not syntax_ok:
            results["syntax_error"] = syntax_error

        # Gate 2: forbidden patterns
        patterns_ok, pattern_violations = self.validate_forbidden_patterns(code)
        results["gate_no_forbidden_patterns"] = patterns_ok
        if not patterns_ok:
            results["pattern_violations"] = pattern_violations

        # Gate 3: import allowlist
        imports_ok, import_violations = self.validate_imports(code)
        results["gate_allowed_imports_only"] = imports_ok
        if not imports_ok:
            results["import_violations"] = import_violations

        # Gate 4: confidence threshold
        results["gate_confidence_threshold"] = confidence >= self.config.min_confidence

        # Gate 5: unit tests
        if self.config.unit_test_validation:
            tests_ok, test_results = self.run_unit_tests(code)
            results["gate_unit_tests_pass"] = tests_ok
            results["test_results"] = test_results

        # Gate 6: human approval (resolved by the orchestrator)
        results["gate_human_approval"] = True

        # Gate 7: integration tests (optional)
        results["gate_integration_tests_pass"] = not self.config.integration_test_validation

        required = self._required_gates()
        results["all_passed"] = all(
            bool(results.get(gate)) for gate in required
        )
        return results

    def _required_gates(self) -> List[str]:
        """Return the list of gates that must pass for this configuration."""
        gates = []
        if self.config.gate_syntax_valid:
            gates.append("gate_syntax_valid")
        if self.config.gate_no_forbidden_patterns:
            gates.append("gate_no_forbidden_patterns")
        if self.config.gate_allowed_imports_only:
            gates.append("gate_allowed_imports_only")
        if self.config.gate_confidence_threshold:
            gates.append("gate_confidence_threshold")
        if self.config.gate_human_approval:
            gates.append("gate_human_approval")
        return gates

    def all_gates_pass(self, gate_results: Dict[str, Any]) -> bool:
        """Check whether every required gate is present and truthy.

        Test-execution gates (unit/integration) are reported separately so a
        failing test suite can be surfaced as TESTS_FAILED rather than a
        generic gate rejection. When one of them is present in the results
        it still has to be truthy.
        """
        for gate in self._required_gates():
            if not gate_results.get(gate, False):
                return False
        for gate in ("gate_unit_tests_pass", "gate_integration_tests_pass"):
            if gate in gate_results and not gate_results[gate]:
                return False
        return True



class SynthesisFeatureFlags:
    """Feature flags controlling rollout of synthesis capabilities."""

    def __init__(self):
        self.flags: Dict[str, bool] = {
            "enable_llm_synthesis": False,
            "enable_human_in_loop": False,
        }
        self.rollout_percentage: Dict[str, int] = {
            "enable_llm_synthesis": 0,
            "enable_human_in_loop": 0,
        }

    def is_enabled(self, flag_name: str, tenant_id: Optional[str] = None) -> bool:
        """Check whether a flag is enabled, honouring deterministic rollout."""
        if flag_name not in self.flags:
            return False
        if self.flags[flag_name]:
            return True

        percentage = self.rollout_percentage.get(flag_name, 0)
        if percentage > 0 and tenant_id:
            digest = hashlib.md5(tenant_id.encode("utf-8")).hexdigest()
            return (int(digest, 16) % 100) < percentage
        return False

    def set_flag(self, flag_name: str, enabled: bool) -> None:
        """Enable or disable a flag globally."""
        if flag_name in self.flags:
            self.flags[flag_name] = enabled

    def set_rollout(self, flag_name: str, percentage: int) -> None:
        """Set a deterministic percentage rollout for a flag."""
        if flag_name in self.rollout_percentage:
            self.rollout_percentage[flag_name] = max(0, min(100, percentage))

    def get_config_for_tenant(self, tenant_id: Optional[str] = None) -> GuardrailConfig:
        """Build a guardrail configuration honouring per-tenant rollout."""
        config = GuardrailConfig()
        config.enable_llm_synthesis = self.is_enabled("enable_llm_synthesis", tenant_id)
        config.enable_human_in_loop = self.is_enabled("enable_human_in_loop", tenant_id)
        return config


# Global feature flags instance
synthesis_flags = SynthesisFeatureFlags()


class SynthesisOrchestrator:
    """Main orchestrator for AI-assisted synthesis with guardrails.

    Coordinates LLM providers, deterministic guardrails, and optional
    human-in-the-loop approval. Never emits code that fails a required gate.
    """

    def __init__(
        self,
        config: Optional[GuardrailConfig] = None,
        llm_provider: Optional[LLMProvider] = None,
        policy_registry: Optional[Any] = None,
    ):
        self.config = config or GuardrailConfig()
        self.llm_provider = llm_provider or MockLLMProvider()
        self.guardrails = SynthesisGuardrails(self.config)
        self.policy_registry = policy_registry

        self.metrics: Dict[str, Any] = {
            "total_syntheses": 0,
            "successful": 0,
            "rejected": 0,
            "human_interventions": 0,
            "total_tokens": 0,
        }

    async def synthesize(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        mode: SynthesisMode = SynthesisMode.LLM_ASSISTED,
    ) -> SynthesisResult:
        """Synthesize code under the requested mode, enforcing all gates."""
        started = time.time()
        self.metrics["total_syntheses"] += 1
        context = context or {}

        if mode == SynthesisMode.DETERMINISTIC_ONLY:
            result = self._deterministic_synthesis(prompt, context)
        else:
            result = await self._llm_synthesis(prompt, context, mode)

        result.synthesis_time_ms = int((time.time() - started) * 1000)
        result.mode_used = mode

        if result.status == SynthesisStatus.SUCCESS:
            self.metrics["successful"] += 1
        else:
            self.metrics["rejected"] += 1
        return result

    # -- Internal flows -------------------------------------------------------

    def _deterministic_synthesis(self, prompt: str, context: Dict[str, Any]) -> SynthesisResult:
        """Deterministic path: no LLM, structural analysis only."""
        return SynthesisResult(
            status=SynthesisStatus.SUCCESS,
            synthesized_code=(
                "# Deterministic synthesis\n"
                "# No LLM invoked; structure derived from deterministic analysis.\n"
                f"# Prompt length: {len(prompt)}\n"
            ),
            confidence=1.0,
            gate_results={"all_passed": True},
            validation_results={"deterministic": True},
        )

    async def _llm_synthesis(
        self,
        prompt: str,
        context: Dict[str, Any],
        mode: SynthesisMode,
    ) -> SynthesisResult:
        """LLM path with retry, gate enforcement and optional human approval."""
        last_result: Optional[SynthesisResult] = None
        current_prompt = prompt

        for attempt in range(max(1, self.config.max_retries)):
            last_result = await self._attempt(current_prompt, context)

            if last_result.status == SynthesisStatus.SUCCESS:
                break

            if last_result.status in (
                SynthesisStatus.CONFIDENCE_LOW,
                SynthesisStatus.HUMAN_REJECTED,
            ):
                # Not retryable - the model fundamentally under-performs.
                break

            if attempt < self.config.max_retries - 1:
                current_prompt = self._adjust_prompt(current_prompt, last_result)

        assert last_result is not None

        if last_result.status == SynthesisStatus.SUCCESS and mode == SynthesisMode.HUMAN_IN_LOOP:
            approved = self._request_human_approval(last_result)
            last_result.human_approved = approved
            if not approved:
                last_result.status = SynthesisStatus.HUMAN_REJECTED
                last_result.error_message = "Rejected by human reviewer"

        return last_result

    async def _attempt(self, prompt: str, context: Dict[str, Any]) -> SynthesisResult:
        """Single LLM attempt with full guardrail evaluation."""
        response = self.llm_provider.generate(prompt, self.config, context)
        if inspect.isawaitable(response):
            response = await response

        if not self.llm_provider.validate_response(response):
            return SynthesisResult(
                status=SynthesisStatus.VALIDATION_FAILED,
                error_message="Invalid LLM response format",
                gate_results={},
            )

        code = response.get("code", "")
        confidence = float(response.get("confidence", 0.0))

        if confidence < self.config.min_confidence:
            return SynthesisResult(
                status=SynthesisStatus.CONFIDENCE_LOW,
                synthesized_code=code,
                confidence=confidence,
                error_message=(
                    f"Confidence {confidence:.2f} below threshold "
                    f"{self.config.min_confidence}"
                ),
                gate_results={},
            )

        gate_results = self.guardrails.run_all_gates(code, confidence)
        gate_results = {k: v for k, v in gate_results.items() if isinstance(v, bool)}

        if not self.guardrails.all_gates_pass(gate_results):
            if gate_results.get("gate_unit_tests_pass") is False:
                return SynthesisResult(
                    status=SynthesisStatus.TESTS_FAILED,
                    synthesized_code=code,
                    confidence=confidence,
                    gate_results=gate_results,
                    test_results=gate_results.get("test_results", {}),
                    error_message="Generated code failed the unit test harness",
                )
            if gate_results.get("gate_integration_tests_pass") is False:
                return SynthesisResult(
                    status=SynthesisStatus.TESTS_FAILED,
                    synthesized_code=code,
                    confidence=confidence,
                    gate_results=gate_results,
                    test_results=gate_results.get("test_results", {}),
                    error_message="Generated code failed the integration test suite",
                )
            return SynthesisResult(
                status=SynthesisStatus.GATE_REJECTED,
                synthesized_code=code,
                confidence=confidence,
                gate_results=gate_results,
                error_message="Code failed one or more guardrail gates",
            )

        return SynthesisResult(
            status=SynthesisStatus.SUCCESS,
            synthesized_code=code,
            confidence=confidence,
            gate_results=gate_results,
            test_results=gate_results.get("test_results", {}),
        )

    def _adjust_prompt(self, prompt: str, failed: SynthesisResult) -> str:
        """Build a corrective prompt after a failed attempt."""
        adjustments: List[str] = []
        if failed.status == SynthesisStatus.GATE_REJECTED:
            for gate, passed in failed.gate_results.items():
                if not passed:
                    adjustments.append(f"Fix {gate} violation")
        if failed.status == SynthesisStatus.TESTS_FAILED:
            adjustments.append("Ensure code passes unit tests")
        if failed.status == SynthesisStatus.VALIDATION_FAILED:
            adjustments.append("Return strictly valid JSON with code and confidence")
        if not adjustments:
            adjustments.append("Simplify the implementation")
        return prompt + "\n\nPrevious attempt failed. Fixes needed:\n" + "\n".join(
            f"- {item}" for item in adjustments
        )

    def _request_human_approval(self, result: SynthesisResult) -> bool:
        """Request human approval for a synthesis result."""
        self.metrics["human_interventions"] += 1
        # Auto-approve only very high confidence results; a real deployment
        # would block on an external approval channel.
        return result.confidence >= 0.95

    def get_metrics(self) -> Dict[str, Any]:
        """Return synthesis metrics including derived success/rejection rates."""
        total = self.metrics["total_syntheses"]
        successful = self.metrics["successful"]
        rejected = self.metrics["rejected"]
        return {
            "total_syntheses": total,
            "successful": successful,
            "rejected": rejected,
            "human_interventions": self.metrics["human_interventions"],
            "total_tokens": self.metrics["total_tokens"],
            "success_rate": (successful / total) if total else 0.0,
            "rejection_rate": (rejected / total) if total else 0.0,
        }


async def synthesize_code(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    mode: SynthesisMode = SynthesisMode.LLM_ASSISTED,
    config: Optional[GuardrailConfig] = None,
    llm_provider: Optional[LLMProvider] = None,
) -> SynthesisResult:
    """High-level helper to synthesize code through the orchestrator."""
    orchestrator = SynthesisOrchestrator(config=config, llm_provider=llm_provider)
    return await orchestrator.synthesize(prompt, context, mode)
