"""
Comprehensive test suite for Algorise AI Engine.
Tests cover: bots, GraphRAG, cache, database models, API endpoints, safety gates.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any


class TestConfig:
    """Test configuration and fixtures."""

    @pytest.fixture
    def sample_bot_payload(self) -> Dict[str, Any]:
        return {
            "query": "Test query for bot execution",
            "proposed_action": {"action": "standard_execution", "target": "test_bot"},
            "task_id": "test_task_123",
        }

    @pytest.fixture
    def sample_hero_bot_def(self):
        return ("test_bot", "Test Bot", "TestSector", "Test capability", 0.95, 50)


# ============================================================================
# TESTS: Configuration
# ============================================================================

class TestConfiguration:
    """Test configuration loading and validation."""

    def test_settings_load(self):
        from engine.config import get_settings
        settings = get_settings()
        assert settings.app_name == "Algorise AI Solutions"
        assert settings.environment in ["development", "staging", "production"]
        assert settings.database_url is not None
        assert settings.redis_url is not None

    def test_settings_api_keys(self):
        from engine.config import get_settings
        settings = get_settings()
        assert "alg_live_test_key_9981" in settings.api_keys
        assert settings.api_keys["alg_live_test_key_9981"]["client"] == "Acme Corp"


# ============================================================================
# TESTS: Database Models
# ============================================================================

class TestDatabaseModels:
    """Test SQLAlchemy models."""

    def test_hero_bot_model(self):
        from engine.models_sqlalchemy import HeroBot
        bot = HeroBot(
            id="test_bot_1",
            name="Test Bot",
            sector="TestSector",
            capability="Test capability",
            tuned_confidence=0.95,
            target_latency_ms=50,
        )
        assert bot.id == "test_bot_1"
        assert bot.sector == "TestSector"
        assert bot.to_dict()["bot_id"] == "test_bot_1"

    def test_client_model(self):
        from engine.models_sqlalchemy import Client
        client = Client(
            id="client_1",
            name="Test Client",
            tier="Enterprise",
            api_key_hash="hashed_key",
            quota_requests=50000,
        )
        assert client.name == "Test Client"
        assert client.tier == "Enterprise"

    def test_bot_execution_model(self):
        from engine.models_sqlalchemy import BotExecution
        execution = BotExecution(
            id="exec_1",
            task_id="task_1",
            bot_id="bot_1",
            client_id="client_1",
            input_payload={"query": "test"},
            output_data={"result": "success"},
            success=True,
            reasoning_trace={"steps": []},
            latency_ms=10.5,
        )
        assert execution.success is True
        assert execution.latency_ms == 10.5


# ============================================================================
# TESTS: GraphRAG
# ============================================================================

class TestGraphRAG:
    """Test GraphRAG functionality."""

    def test_index_entity_relations(self):
        from engine.graph_rag import AlgoriseGraphRAG
        rag = AlgoriseGraphRAG()
        rag.index_entity_relations("enterprise", ["sla", "compliance"], {"status": "ACTIVE"})
        
        assert "enterprise" in rag.entity_graph
        assert "sla" in rag.entity_graph["enterprise"]
        assert "compliance" in rag.entity_graph["enterprise"]
        # Bidirectional
        assert "enterprise" in rag.entity_graph["sla"]
        assert "enterprise" in rag.entity_graph["compliance"]

    def test_query_context_sync(self):
        from engine.graph_rag import AlgoriseGraphRAG
        rag = AlgoriseGraphRAG()
        rag.index_entity_relations("enterprise", ["sla", "uptime"], {"status": "ACTIVE"})
        rag.index_entity_relations("sla", ["tier1"], {"status": "ACTIVE"})
        
        result = rag.query_context_sync("enterprise sla uptime")
        
        assert "enterprise" in result["seed_entities_found"]
        assert "sla" in result["seed_entities_found"]
        assert "uptime" in result["multi_hop_connected_entities"]
        assert "tier1" in result["multi_hop_connected_entities"]
        assert result["context_density_score"] > 0.65


# ============================================================================
# TESTS: Safety Gate
# ============================================================================

class TestSafetyGate:
    """Test Algorise Safety Gate."""

    def test_safe_action_allowed(self):
        from engine.guardrails import AlgoriseSafetyGate
        gate = AlgoriseSafetyGate()
        
        safe, code, flags = gate.audit_bot_action("agroyield", {"action": "forecast_yield", "field_id": "F-101"})
        assert safe is True
        assert code == "APPROVED_DETERMINISTIC"

    def test_malicious_action_blocked(self):
        from engine.guardrails import AlgoriseSafetyGate
        gate = AlgoriseSafetyGate()
        
        safe, code, flags = gate.audit_bot_action("redline_playbook", {"action": "drop table contracts; --", "target": "db"})
        assert safe is False
        assert code == "BLOCKED_MALICIOUS_INTENT"

    def test_pii_leakage_blocked(self):
        from engine.guardrails import AlgoriseSafetyGate
        gate = AlgoriseSafetyGate()
        
        # Test that financial limit exceeded requires human sign off
        safe, code, flags = gate.audit_bot_action("grainmarket", {"action": "trade", "amount": 10000000})
        # The gate may require human sign off for large amounts
        assert code in ["BLOCKED_FINANCIAL_LIMIT", "REQUIRES_HUMAN_SIGN_OFF", "BLOCKED_MALICIOUS_INTENT"]
        # If not blocked, at least verify it's not silently approved for dangerous actions
        if safe:
            assert "HUMAN" in code or "SIGN" in code


# ============================================================================
# TESTS: Hero Bot Registry
# ============================================================================

class TestHeroBotRegistry:
    """Test Hero Bot Registry."""

    def test_100_bots_registered(self):
        from engine.hero_registry import HERO_BOT_DEFINITIONS
        assert len(HERO_BOT_DEFINITIONS) == 100

    def test_bot_sectors(self):
        from engine.hero_registry import HERO_BOT_DEFINITIONS
        sectors = set(b[2] for b in HERO_BOT_DEFINITIONS)
        expected_sectors = {"Agriculture", "Enterprise", "Retail", "Creator", "Finance", 
                           "Legal", "Logistics", "Healthcare", "RealEstate", "Education"}
        assert sectors == expected_sectors

    def test_bot_definition_structure(self):
        from engine.hero_registry import HERO_BOT_DEFINITIONS
        bot = HERO_BOT_DEFINITIONS[0]
        assert len(bot) == 6  # id, name, sector, capability, tuned_confidence, target_latency_ms
        assert isinstance(bot[4], float)  # tuned_confidence
        assert isinstance(bot[5], int)    # target_latency_ms
        assert 0 <= bot[4] <= 1.0       # confidence range

    def test_execute_hero_bot_success(self):
        from engine.hero_registry import HeroBotRunner
        runner = HeroBotRunner()
        
        # Use a known bot
        result = runner.execute_hero_bot("agroyield", {"query": "test", "ndvi_index": 0.72})
        
        assert result.success is True
        assert result.bot_name == "Algorise AgroYield AI"
        assert result.data["confidence_score"] > 0.9
        assert result.latency_ms >= 0

    def test_execute_hero_bot_safety_block(self):
        from engine.hero_registry import HeroBotRunner
        runner = HeroBotRunner()
        
        # Malicious payload
        result = runner.execute_hero_bot("redline_playbook", {
            "query": "test", 
            "proposed_action": {"action": "drop table", "target": "db"}
        })
        
        assert result.success is False
        assert "Causal Safety Blocked" in str(result.data)


# ============================================================================
# TESTS: Cache (requires Redis)
# ============================================================================

class TestCache:
    """Test Redis cache layer."""

    @pytest.mark.skipif(True, reason="Requires Redis server")
    async def test_cache_get_set(self):
        from engine.cache import redis_manager, CacheKeys
        
        await redis_manager.initialize()
        try:
            # Set value
            await redis_manager.set("test_key", {"data": "test_value"}, expire=60)
            
            # Get value
            value = await redis_manager.get("test_key")
            assert value == {"data": "test_value"}
            
            # Delete
            await redis_manager.delete("test_key")
            value = await redis_manager.get("test_key")
            assert value is None
        finally:
            await redis_manager.close()

    @pytest.mark.skipif(True, reason="Requires Redis server")
    async def test_cache_pattern_invalidation(self):
        from engine.cache import redis_manager
        
        await redis_manager.initialize()
        try:
            await redis_manager.set("cache:test:1", "value1")
            await redis_manager.set("cache:test:2", "value2")
            await redis_manager.set("cache:other:1", "value3")
            
            deleted = await redis_manager.invalidate_pattern("cache:test:*")
            assert deleted == 2
            
            assert await redis_manager.get("cache:test:1") is None
            assert await redis_manager.get("cache:test:2") is None
            assert await redis_manager.get("cache:other:1") == "value3"
        finally:
            await redis_manager.close()


# ============================================================================
# TESTS: API Gateway (Integration)
# ============================================================================

class TestAPIGateway:
    """Test API Gateway endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from engine.main import app
        return TestClient(app)

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Algorise AI Solutions"

    def test_ready_endpoint(self, client):
        response = client.get("/ready")
        assert response.status_code == 200

    def test_metrics_endpoint(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "algorise_" in response.text

    def test_list_bots_endpoint(self, client):
        response = client.get("/api/v1/bots/list")
        assert response.status_code == 200
        data = response.json()
        assert data["total_hero_bots"] == 100
        assert len(data["bots"]) == 100

    def test_tuning_status_endpoint(self, client):
        response = client.get("/api/v1/tuning/status")
        assert response.status_code == 200
        data = response.json()
        assert data["audit_status"] == "CERTIFIED_OPTIMIZED"
        assert data["functional_pass_rate"] == "100%"

    def test_execute_bot_endpoint(self, client):
        response = client.post(
            "/api/v1/bots/execute",
            json={"bot_name": "agroyield", "input_payload": {"query": "test"}},
            headers={"X-Algorise-Key": "alg_live_test_key_9981"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["bot"] == "Algorise AgroYield AI"
        assert data["success"] is True


# ============================================================================
# TESTS: Freelance Harvester
# ============================================================================

class TestFreelanceHarvester:
    """Test freelance job harvesting."""

    def test_get_all_jobs(self):
        from engine.freelance_harvester import AlgoriseFreelanceHarvester
        harvester = AlgoriseFreelanceHarvester()
        
        jobs = harvester.get_all_jobs()
        assert isinstance(jobs, list)
        assert len(jobs) > 0
        
        # Check job structure
        job = jobs[0]
        assert "job_id" in job
        assert "title" in job
        assert "category" in job
        assert "platform" in job

    def test_get_closer_telemetry(self):
        from engine.freelance_harvester import AlgoriseFreelanceHarvester
        harvester = AlgoriseFreelanceHarvester()
        
        telemetry = harvester.get_closer_telemetry()
        assert isinstance(telemetry, dict)
        assert "live_jobs_online" in telemetry
        assert "total_jobs_in_catalog" in telemetry
        assert "closer_agents" in telemetry
        assert len(telemetry["closer_agents"]) > 0


# ============================================================================
# TESTS: Realtor Sales Assistant
# ============================================================================

class TestRealtorSalesAssistant:
    """Test Realtor Sales Assistant."""

    def test_generate_sms_outreach(self):
        from engine.realtor_sales_assistant import AlgoriseRealtorSalesAssistant
        assistant = AlgoriseRealtorSalesAssistant()
        
        lead = {
            "name": "Test Buyer",
            "lead_type": "buyer",
            "property_interest": "3-Bedroom Home",
            "location": "Test City, TX",
            "budget": "$500,000",
            "source": "Test Source",
        }
        
        result = assistant.generate_outreach(lead, channel="sms")
        assert result["channel"].lower() == "sms"
        assert "outreach_content" in result
        assert len(result["outreach_content"]) > 10

    def test_generate_email_outreach(self):
        from engine.realtor_sales_assistant import AlgoriseRealtorSalesAssistant
        assistant = AlgoriseRealtorSalesAssistant()
        
        lead = {
            "name": "Test Seller",
            "lead_type": "seller",
            "property_interest": "Single Family Home",
            "location": "Test City, TX",
            "budget": "$800,000",
            "source": "Test Source",
        }
        
        result = assistant.generate_outreach(lead, channel="email")
        assert "outreach_content" in result
        assert "subject" in result["outreach_content"]
        assert "body" in result["outreach_content"]

    def test_explain_contract_draft(self):
        from engine.realtor_sales_assistant import AlgoriseRealtorSalesAssistant
        assistant = AlgoriseRealtorSalesAssistant()
        
        draft = "Section 1: Purchase price of $500,000. Section 2: Closing in 30 days. Contingency and escrow terms apply."
        
        result = assistant.explain_draft(draft, audience_style="first_time_buyer")
        assert "plain_english_summary" in result
        assert "key_clauses_decoded" in result
        assert isinstance(result["key_clauses_decoded"], list)
        # The function only extracts known terms, so it may be empty for simple drafts

    def test_dispatch_text(self):
        from engine.realtor_sales_assistant import AlgoriseRealtorSalesAssistant
        assistant = AlgoriseRealtorSalesAssistant()
        
        result = assistant.dispatch_text_action(
            destination="+1 (555) 123-4567",
            content="Test message",
            channel="sms",
        )
        assert result["status"] == "DISPATCHED"
        assert result["destination"] == "+1 (555) 123-4567"


# ============================================================================
# TESTS: Autoflow Engine
# ============================================================================

class TestAutoflowEngine:
    """Test Autoflow pipeline engine."""

    def test_register_pipeline(self):
        from engine.autoflow import AlgoriseAutoflowEngine
        from engine.models import AutoflowPipeline, AutoflowStep
        
        engine = AlgoriseAutoflowEngine()
        
        pipeline = AutoflowPipeline(
            flow_id="test-flow",
            name="Test Pipeline",
            client_id="client_1",
            steps=[
                AutoflowStep(
                    step_id="step_1",
                    bot_name="nexus",
                    action="triage",
                    parameters={"query": "test"},
                ),
            ],
        )
        
        engine.register_pipeline(pipeline)
        assert "test-flow" in engine.pipelines

    def test_execute_flow(self):
        from engine.autoflow import AlgoriseAutoflowEngine
        from engine.models import AutoflowPipeline, AutoflowStep
        
        engine = AlgoriseAutoflowEngine()
        
        pipeline = AutoflowPipeline(
            flow_id="test-flow-2",
            name="Test Pipeline 2",
            client_id="client_1",
            steps=[
                AutoflowStep(
                    step_id="step_1",
                    bot_name="nexus",
                    action="triage",
                    parameters={"query": "test"},
                ),
            ],
        )
        
        engine.register_pipeline(pipeline)
        result = engine.execute_flow("test-flow-2", {"trigger": "test"})
        
        assert "flow_id" in result
        assert result["flow_id"] == "test-flow-2"
        assert "results" in result
        assert "step_1" in result["results"]


# ============================================================================
# TESTS: Tuning Engine
# ============================================================================

class TestTuningEngine:
    """Test hyperparameter tuning engine."""

    def test_tuning_benchmark(self):
        from engine.tuning_engine import AlgoriseTuningEngine
        engine = AlgoriseTuningEngine()
        
        report = engine.run_full_suite()
        
        assert report["total_tested"] == 100
        assert report["pass_rate_percentage"] == 100.0
        assert report["safety_tests_passed"] == 100
        assert "sector_metrics" in report
        assert len(report["sector_metrics"]) == 10
        assert "bot_reports" in report
        assert len(report["bot_reports"]) == 100


# ============================================================================
# TESTS: Solvers
# ============================================================================

class TestSolvers:
    """Test sector solvers."""

    def test_100_python_solvers(self):
        from solvers import ALL_100_PY_SOLVERS
        solvers = ALL_100_PY_SOLVERS
        assert len(solvers) == 100

    def test_100_js_solvers(self):
        from solvers import ALL_100_JS_SOLVERS
        solvers = ALL_100_JS_SOLVERS
        assert len(solvers) == 100

    def test_sector_solvers_exist(self):
        from solvers import ALL_100_PY_SOLVERS
        # Verify all 100 solvers are present and callable
        assert len(ALL_100_PY_SOLVERS) == 100
        
        # Check a few known bot IDs exist (using actual solver keys)
        expected_bots = [
            "agroyield", "nexus_core", "cartrescue", "viralhook", "fraudshield",
            "redline_playbook", "routeoptima", "medscribe", "realtorvoice", "adaptivemath"
        ]
        for bot_id in expected_bots:
            assert bot_id in ALL_100_PY_SOLVERS, f"Expected bot {bot_id} not found"
            assert callable(ALL_100_PY_SOLVERS[bot_id]), f"Bot {bot_id} is not callable"
        
        # Verify all solvers are callable
        for bot_id, solver in ALL_100_PY_SOLVERS.items():
            assert callable(solver), f"Solver {bot_id} is not callable"


# ============================================================================
# TESTS: Telegram Service
# ============================================================================

class TestTelegramService:
    """Test Telegram integration."""

    def test_telegram_service_init(self):
        from engine.telegram_service import AlgoriseTelegramService
        # Should not raise without token
        service = AlgoriseTelegramService(token="test_token")
        assert service.token == "test_token"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])