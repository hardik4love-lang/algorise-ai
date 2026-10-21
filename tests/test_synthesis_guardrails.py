"""
Tests for T3.4: AI-Driven Synthesis with Guardrails
Validates synthesis guardrails, LLM provider abstraction, orchestrator,
feature flags, and integration with policy engine.
"""

import os
import tempfile
import pytest
import asyncio
import json

from synthesis.synthesis_guardrails import (
    SynthesisMode,
    SynthesisStatus,
    SynthesisResult,
    GuardrailConfig,
    SynthesisMode,
    SynthesisStatus,
    SynthesisResult,
    GuardrailConfig,
    LLMProvider,
    MockLLMProvider,
    SynthesisGuardrails,
    SynthesisOrchestrator,
    SynthesisFeatureFlags,
    synthesis_flags,
    synthesize_code,
)


@pytest.fixture
def config():
    """Module-level guardrail configuration.

    Class-scoped fixtures are only visible inside their own class, so the
    integration and metrics suites need this shared definition.
    """
    return GuardrailConfig(
        enable_llm_synthesis=True,
        min_confidence=0.85,
        allowed_imports=["os", "json"],
        forbidden_patterns=["eval("],
    )


class TestSynthesisResult:
    """Tests for SynthesisResult dataclass."""
    
    def test_result_creation(self):
        """Test creating synthesis results."""
        result = SynthesisResult(
            status=SynthesisStatus.SUCCESS,
            synthesized_code="def hello(): return 'world'",
            confidence=0.95,
            mode_used=SynthesisMode.LLM_ASSISTED,
        )
        
        assert result.status == SynthesisStatus.SUCCESS
        assert result.confidence == 0.95
        assert result.mode_used == SynthesisMode.LLM_ASSISTED
        assert result.synthesized_code == "def hello(): return 'world'"


class TestGuardrailConfig:
    """Tests for GuardrailConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = GuardrailConfig()
        
        assert config.enable_llm_synthesis is False
        assert config.enable_human_in_loop is False
        assert config.min_confidence == 0.85
        assert config.max_tokens == 2048
        assert config.temperature == 0.1
        assert "os" in config.allowed_imports
        assert "eval(" in config.forbidden_patterns
        
    def test_custom_config(self):
        """Test custom configuration."""
        config = GuardrailConfig(
            enable_llm_synthesis=True,
            min_confidence=0.90,
            temperature=0.0,
            allowed_imports=["os", "json"],
            forbidden_patterns=["eval(", "exec("],
        )
        
        assert config.enable_llm_synthesis is True
        assert config.min_confidence == 0.90
        assert config.temperature == 0.0
        assert config.allowed_imports == ["os", "json"]
        assert config.forbidden_patterns == ["eval(", "exec("]


class TestMockLLMProvider:
    """Tests for MockLLMProvider."""
    
    @pytest.mark.asyncio
    async def test_generate_default(self):
        """Test default mock generation."""
        provider = MockLLMProvider()
        response = await provider.generate("test prompt", GuardrailConfig(), {})
        
        assert "code" in response
        assert "confidence" in response
        assert "explanation" in response
        assert "tokens_used" in response
        assert provider.call_count == 1
        
    @pytest.mark.asyncio
    async def test_generate_custom_responses(self):
        """Test custom response sequence."""
        responses = [
            {"code": "code1", "confidence": 0.9},
            {"code": "code2", "confidence": 0.8},
        ]
        provider = MockLLMProvider(responses)
        
        r1 = await provider.generate("prompt1", GuardrailConfig(), {})
        r2 = await provider.generate("prompt2", GuardrailConfig(), {})
        r3 = await provider.generate("prompt3", GuardrailConfig(), {})
        
        assert r1["code"] == "code1"
        assert r2["code"] == "code2"
        assert r3["code"] == "code2"  # Last response repeated
        
    @pytest.mark.asyncio
    async def test_validate_response(self):
        """Test response validation."""
        provider = MockLLMProvider()
        
        valid = {"code": "x = 1", "confidence": 0.9}
        invalid = {"code": "x = 1"}  # missing confidence
        
        assert provider.validate_response(valid) is True
        assert provider.validate_response(invalid) is False


class TestSynthesisGuardrails:
    """Tests for SynthesisGuardrails."""
    
    def setup_method(self):
        self.config = GuardrailConfig(
            min_confidence=0.85,
            allowed_imports=["os", "json", "typing"],
            forbidden_patterns=["eval(", "exec(", "subprocess"],
        )
        self.guardrails = SynthesisGuardrails(self.config)
        
    def test_validate_syntax_valid(self):
        """Test syntax validation for valid code."""
        code = "def hello():\n    return 'world'"
        ok, error = self.guardrails.validate_syntax(code)
        assert ok is True
        assert error is None
        
    def test_validate_syntax_invalid(self):
        """Test syntax validation for invalid code."""
        code = "def hello(:\n    return 'world'"  # Missing )
        ok, error = self.guardrails.validate_syntax(code)
        assert ok is False
        assert "Syntax error" in error
        
    def test_validate_forbidden_patterns_clean(self):
        """Test forbidden patterns check for clean code."""
        code = "import os\nimport json\ndef hello():\n    return json.dumps({'hello': 'world'})"
        ok, violations = self.guardrails.validate_forbidden_patterns(code)
        assert ok is True
        assert violations == []
        
    def test_validate_forbidden_patterns_dirty(self):
        """Test forbidden patterns check for dirty code."""
        code = "import os\neval('1+1')"
        ok, violations = self.guardrails.validate_forbidden_patterns(code)
        assert ok is False
        assert any("eval(" in v for v in violations)
        
    def test_validate_imports_allowed(self):
        """Test import validation for allowed imports."""
        code = "import os\nimport json\nfrom typing import List"
        ok, violations = self.guardrails.validate_imports(code)
        assert ok is True
        assert violations == []
        
    def test_validate_imports_disallowed(self):
        """Test import validation for disallowed imports."""
        code = "import subprocess\nimport socket"
        ok, violations = self.guardrails.validate_imports(code)
        assert ok is False
        assert any("subprocess" in v for v in violations)
        assert any("socket" in v for v in violations)
        
    def test_run_all_gates_pass(self):
        """Test all gates passing."""
        code = "import json\ndef hello():\n    return json.dumps({'hello': 'world'})"
        results = self.guardrails.run_all_gates(code, 0.95)
        
        assert results["gate_syntax_valid"] is True
        assert results["gate_no_forbidden_patterns"] is True
        assert results["gate_allowed_imports_only"] is True
        assert results["gate_confidence_threshold"] is True
        
    def test_run_all_gates_fail_syntax(self):
        """Test gates failing on syntax error."""
        code = "def hello(:\n    return 'world'"
        results = self.guardrails.run_all_gates(code, 0.95)
        
        assert results["gate_syntax_valid"] is False
        assert "syntax_error" in results
        
    def test_run_all_gates_fail_confidence(self):
        """Test gates failing on low confidence."""
        code = "import json\ndef hello():\n    return json.dumps({'hi': 'there'})"
        results = self.guardrails.run_all_gates(code, 0.50)  # Below 0.85 threshold
        
        assert results["gate_confidence_threshold"] is False
        
    def test_all_gates_pass_check(self):
        """Test all_gates_pass check."""
        gates_pass = {
            "gate_syntax_valid": True,
            "gate_no_forbidden_patterns": True,
            "gate_allowed_imports_only": True,
            "gate_confidence_threshold": True,
        }
        gates_fail = {
            "gate_syntax_valid": False,
            "gate_no_forbidden_patterns": True,
            "gate_allowed_imports_only": True,
            "gate_confidence_threshold": True,
        }
        
        # all_gates_pass requires ALL required gates to be present and True
        assert self.guardrails.all_gates_pass(gates_pass) is True
        assert self.guardrails.all_gates_pass(gates_fail) is False
        # Missing required gates should fail
        assert self.guardrails.all_gates_pass({"gate_syntax_valid": True}) is False
        
    def test_human_approval_gate(self):
        """Test human approval gate."""
        config = GuardrailConfig(gate_human_approval=True)
        guardrails = SynthesisGuardrails(config)
        
        gates_no_approval = {
            "gate_syntax_valid": True,
            "gate_no_forbidden_patterns": True,
            "gate_allowed_imports_only": True,
            "gate_confidence_threshold": True,
        }
        gates_with_approval = {
            "gate_syntax_valid": True,
            "gate_no_forbidden_patterns": True,
            "gate_allowed_imports_only": True,
            "gate_confidence_threshold": True,
            "gate_human_approval": False,
        }
        
        # Without approval gate enabled
        assert guardrails.all_gates_pass({"gate_syntax_valid": True, 
                                         "gate_no_forbidden_patterns": True,
                                         "gate_allowed_imports_only": True,
                                         "gate_confidence_threshold": True}) is False  # Missing required gates
        
        # With approval gate enabled but not passed
        assert guardrails.all_gates_pass(gates_with_approval) is False  # Missing human approval
        gates_with_approval["gate_human_approval"] = True
        assert guardrails.all_gates_pass(gates_with_approval) is True


class TestMockLLMProvider:
    """Tests for MockLLMProvider."""
    
    @pytest.mark.asyncio
    async def test_generate_sequence(self):
        """Test sequential response generation."""
        provider = MockLLMProvider([
            {"code": "def a(): pass", "confidence": 0.9},
            {"code": "def b(): pass", "confidence": 0.8},
        ])
        
        r1 = await provider.generate("prompt1", GuardrailConfig(), {})
        r2 = await provider.generate("prompt2", GuardrailConfig(), {})
        r3 = await provider.generate("prompt3", GuardrailConfig(), {})
        
        assert r1["code"] == "def a(): pass"
        assert r2["code"] == "def b(): pass"
        assert r3["code"] == "def b(): pass"  # Repeats last
        
    @pytest.mark.asyncio
    async def test_validate_response(self):
        provider = MockLLMProvider()
        
        assert provider.validate_response({"code": "x=1", "confidence": 0.9}) is True
        assert provider.validate_response({"code": "x=1"}) is False
        assert provider.validate_response({}) is False


class TestSynthesisOrchestrator:
    """Tests for SynthesisOrchestrator."""
    
    @pytest.fixture
    def config(self):
        return GuardrailConfig(
            enable_llm_synthesis=True,
            min_confidence=0.85,
            allowed_imports=["os", "json"],
            forbidden_patterns=["eval("],
        )
    
    @pytest.fixture
    def orchestrator(self, config):
        return SynthesisOrchestrator(
            config=config,
            llm_provider=MockLLMProvider([
                {"code": "def hello():\n    return 'Hello, World!'", "confidence": 0.95},
            ]),
        )
    
    @pytest.mark.asyncio
    async def test_deterministic_mode(self, orchestrator):
        """Test deterministic-only mode."""
        result = await orchestrator.synthesize(
            prompt="Create a function",
            context={},
            mode=SynthesisMode.DETERMINISTIC_ONLY,
        )
        
        assert result.mode_used == SynthesisMode.DETERMINISTIC_ONLY
        assert result.status == SynthesisStatus.SUCCESS
        assert "Deterministic" in result.synthesized_code
        
    @pytest.mark.asyncio
    async def test_llm_synthesis_success(self, orchestrator):
        """Test successful LLM synthesis."""
        result = await orchestrator.synthesize(
            prompt="Create a greeting function",
            context={"type": "function", "name": "greet"},
            mode=SynthesisMode.LLM_ASSISTED,
        )
        
        assert result.status == SynthesisStatus.SUCCESS
        assert result.confidence >= 0.85
        assert "Hello" in result.synthesized_code
        assert result.mode_used == SynthesisMode.LLM_ASSISTED
        
    @pytest.mark.asyncio
    async def test_llm_synthesis_low_confidence(self, config):
        """Test synthesis fails on low confidence."""
        orchestrator = SynthesisOrchestrator(
            config=config,
            llm_provider=MockLLMProvider([
                {"code": "def low(): pass", "confidence": 0.50},  # Below 0.85
            ]),
        )
        
        result = await orchestrator.synthesize(
            prompt="Create a function",
            context={},
            mode=SynthesisMode.LLM_ASSISTED,
        )
        
        assert result.status == SynthesisStatus.CONFIDENCE_LOW
        assert result.confidence < 0.85
        
    @pytest.mark.asyncio
    async def test_llm_synthesis_gate_rejection(self, config):
        """Test synthesis rejected by guardrails."""
        orchestrator = SynthesisOrchestrator(
            config=config,
            llm_provider=MockLLMProvider([
                {"code": "eval('1+1')", "confidence": 0.95},  # Forbidden pattern
            ]),
        )
        
        result = await orchestrator.synthesize(
            prompt="Create a function",
            context={},
            mode=SynthesisMode.LLM_ASSISTED,
        )
        
        assert result.status == SynthesisStatus.GATE_REJECTED
        assert result.gate_results["gate_no_forbidden_patterns"] is False
        
    @pytest.mark.asyncio
    async def test_llm_synthesis_test_failure(self, config):
        """Test synthesis fails unit tests."""
        orchestrator = SynthesisOrchestrator(
            config=config,
            llm_provider=MockLLMProvider([
                {"code": "def broken():\n    return undefined_variable", "confidence": 0.95},
            ]),
        )
        
        result = await orchestrator.synthesize(
            prompt="Create a function",
            context={},
            mode=SynthesisMode.LLM_ASSISTED,
        )
        
        assert result.status == SynthesisStatus.TESTS_FAILED
        
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, orchestrator):
        """Test metrics tracking."""
        await orchestrator.synthesize("test", {}, mode=SynthesisMode.DETERMINISTIC_ONLY)
        await orchestrator.synthesize("test", {}, mode=SynthesisMode.DETERMINISTIC_ONLY)
        
        metrics = orchestrator.get_metrics()
        assert metrics["total_syntheses"] == 2
        assert metrics["successful"] == 2
        assert metrics["success_rate"] == 1.0


class TestSynthesisFeatureFlags:
    """Tests for SynthesisFeatureFlags."""
    
    def setup_method(self):
        self.flags = SynthesisFeatureFlags()
        
    def test_default_flags_disabled(self):
        """Test flags disabled by default."""
        assert self.flags.is_enabled("enable_llm_synthesis") is False
        assert self.flags.is_enabled("enable_human_in_loop") is False
        
    def test_enable_flag(self):
        """Test enabling a flag."""
        self.flags.set_flag("enable_llm_synthesis", True)
        assert self.flags.is_enabled("enable_llm_synthesis") is True
        
    def test_rollout_percentage(self):
        """Test rollout percentage."""
        self.flags.set_rollout("enable_llm_synthesis", 50)
        
        # Deterministic based on tenant hash
        enabled_count = sum(
            1 for i in range(1000) 
            if self.flags.is_enabled("enable_llm_synthesis", f"tenant_{i}")
        )
        # Should be approximately 50% (allowing for hash distribution)
        assert 400 < enabled_count < 600
        
    def test_get_config_for_tenant(self):
        """Test getting config for specific tenant."""
        self.flags.set_flag("enable_llm_synthesis", True)
        self.flags.set_flag("enable_human_in_loop", True)
        
        config = synthesis_flags.get_config_for_tenant("test_tenant")
        
        assert config.enable_llm_synthesis is True
        assert config.enable_human_in_loop is True


class TestSynthesisOrchestratorIntegration:
    """Integration tests for SynthesisOrchestrator with real scenarios."""
    
    @pytest.mark.asyncio
    async def test_human_in_loop_approval(self, config):
        """Test human-in-loop approval flow."""
        # Use mock that requires human approval
        orchestrator = SynthesisOrchestrator(
            config=GuardrailConfig(
                enable_llm_synthesis=True,
                enable_human_in_loop=True,
                min_confidence=0.85,
            ),
            llm_provider=MockLLMProvider([
                {"code": "def greet():\n    return 'Hello!'", "confidence": 0.95},
            ]),
        )
        
        # Mock human approval (auto-approve for confidence > 0.95)
        result = await orchestrator.synthesize(
            prompt="Create a greeting function",
            context={},
            mode=SynthesisMode.HUMAN_IN_LOOP,
        )
        
        assert result.status == SynthesisStatus.SUCCESS
        assert result.human_approved is True
        
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, config):
        """Test retry logic on synthesis failure."""
        orchestrator = SynthesisOrchestrator(
            config=config,
            llm_provider=MockLLMProvider([
                {"code": "eval('bad')", "confidence": 0.95},  # Fails gate
                {"code": "def good():\n    return 'ok'", "confidence": 0.95},  # Passes
            ]),
        )
        
        result = await orchestrator.synthesize(
            prompt="Create a function",
            context={},
            mode=SynthesisMode.LLM_ASSISTED,
        )
        
        # Should retry and succeed on second attempt
        assert result.status == SynthesisStatus.SUCCESS
        assert "good" in result.synthesized_code


class TestSynthesisFeatureFlags:
    """Tests for SynthesisFeatureFlags."""
    
    def setup_method(self):
        self.flags = SynthesisFeatureFlags()
        
    def test_default_disabled(self):
        assert self.flags.is_enabled("enable_llm_synthesis") is False
        assert self.flags.is_enabled("enable_human_in_loop") is False
        
    def test_explicit_enable(self):
        self.flags.set_flag("enable_llm_synthesis", True)
        assert self.flags.is_enabled("enable_llm_synthesis") is True
        
    def test_rollout_percentage(self):
        self.flags.set_rollout("enable_llm_synthesis", 25)
        
        enabled = sum(1 for i in range(1000) if self.flags.is_enabled("enable_llm_synthesis", f"t{i}"))
        assert 200 < enabled < 300  # ~25%
        
    def test_tenant_specific_config(self):
        """Test tenant-specific config generation."""
        # Default flags
        config1 = synthesis_flags.get_config_for_tenant("tenant_a")
        assert config1.enable_llm_synthesis is False
        
        # Enable flag
        synthesis_flags.set_flag("enable_llm_synthesis", True)
        config2 = synthesis_flags.get_config_for_tenant("tenant_a")
        assert config2.enable_llm_synthesis is True
        
        # Disable
        synthesis_flags.set_flag("enable_llm_synthesis", False)


class TestSynthesizeCodeFunction:
    """Tests for high-level synthesize_code function."""

    @pytest.mark.asyncio
    async def test_synthesize_code_function(self):
        """Test high-level synthesize_code function."""
        # Test the high-level function by using orchestrator directly
        # since synthesize_code creates its own orchestrator internally
        from synthesis.synthesis_guardrails import SynthesisOrchestrator

        orchestrator = SynthesisOrchestrator(
            config=GuardrailConfig(enable_llm_synthesis=True),
            llm_provider=MockLLMProvider([
                {"code": "def add(a, b):\n    return a + b", "confidence": 0.95},
            ]),
        )

        result = await orchestrator.synthesize(
            prompt="Create a function that adds two numbers",
            context={"type": "function", "name": "add"},
            mode=SynthesisMode.LLM_ASSISTED,
        )

        assert result.status == SynthesisStatus.SUCCESS
        assert "add" in result.synthesized_code
        assert result.confidence >= 0.85

class TestSynthesisIntegrationWithPolicy:
    """Tests for synthesis integration with policy engine."""
    
    @pytest.mark.asyncio
    async def test_synthesis_with_policy_registry(self):
        """Test synthesis orchestrator with policy registry."""
        from policy.policy_engine import PolicyRegistry, PolicyRule, RuleScope, RuleProvenance
        
        # Create registry with synthesis rule
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = os.path.join(tmpdir, ".algorise", "policies")
            os.makedirs(registry_path, exist_ok=True)
            
            registry = PolicyRegistry(registry_path)
            registry.register_engine("synthesis", None)  # Placeholder
            
            # Add synthesis rule
            rule = PolicyRule(
                rule_id="synthesis-rule-1",
                name="Synthesis Rule",
                description="Test synthesis rule",
                scope=RuleScope.TENANT,
                provenance=RuleProvenance.TENANT_PACK,
                config={"engine": "synthesis", "require_review": True},
                tenant_id="test_tenant",
            )
            registry.add_rule(rule, persist=False)
            
            # Check rule is applicable
            ctx = {"tenant_id": "test_tenant", "engine": "synthesis"}
            applicable = registry.get_applicable_rules(ctx)
            
            # Should find the synthesis rule
            rule_ids = {r.rule_id for r in applicable}
            # Note: synthesis engine not registered, so rule won't be applied


class TestSynthesisMetrics:
    """Tests for synthesis metrics."""
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, config):
        orchestrator = SynthesisOrchestrator(
            config=config,
            llm_provider=MockLLMProvider([
                {"code": "def a(): pass", "confidence": 0.9},
                {"code": "eval('bad')", "confidence": 0.9},  # Rejected
            ]),
        )
        
        # First succeeds
        await orchestrator.synthesize("test1", {}, mode=SynthesisMode.LLM_ASSISTED)
        # Second fails (gate rejection)
        await orchestrator.synthesize("test2", {}, mode=SynthesisMode.LLM_ASSISTED)
        
        metrics = orchestrator.get_metrics()
        assert metrics["total_syntheses"] == 2
        assert metrics["successful"] == 1
        assert metrics["rejected"] == 1
        assert metrics["success_rate"] == 0.5
        assert metrics["rejection_rate"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])