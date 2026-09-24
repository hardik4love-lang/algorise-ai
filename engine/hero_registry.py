"""
Algorise Hero 100 Bot Registry
Defines, configures, and routes execution for all 100 proprietary hero bots across 10 industry sectors.
"""

from typing import Dict, Any, List, Optional
import time
import re
import hashlib
import json
from .models import BotTask, BotResult
from .guardrails import AlgoriseSafetyGate
from .graph_rag import AlgoriseGraphRAG
from .cache import redis_manager, CacheKeys

# The 100 Hero Bots Specification Metadata
HERO_BOT_DEFINITIONS = [
    # Sector 1: Agriculture & AgTech
    ("agroyield", "Algorise AgroYield AI", "Agriculture", "Predictive harvest yield forecasting via satellite NDVI & soil regression", 0.94, 50),
    ("florascan", "Algorise FloraScan Edge", "Agriculture", "Computer vision pest & crop disease identification from drone photos", 0.92, 45),
    ("hydrosense", "Algorise HydroSense Closed-Loop", "Agriculture", "Closed-loop precision irrigation optimization via IoT soil sensors", 0.96, 40),
    ("grainmarket", "Algorise GrainMarket Hedger", "Agriculture", "Commodity futures price arbitrage and forward-contract hedging advisor", 0.91, 55),
    ("cattlepulse", "Algorise CattlePulse BioTelemetry", "Agriculture", "Livestock rumination & biometric anomaly illness detector", 0.95, 35),
    ("ecocarbon", "Algorise EcoCarbon MRV", "Agriculture", "Satellite-based carbon credit MRV & soil carbon audit calculator", 0.93, 60),
    ("spraytarget", "Algorise SprayTarget Vision", "Agriculture", "Millisecond weed discrimination and micro-spraying controller", 0.97, 25),
    ("farmfleet", "Algorise FarmFleet Autonomous", "Agriculture", "Autonomous tractor trajectory planning and predictive maintenance", 0.95, 45),
    ("coldchain_ag", "Algorise ColdChain Ag", "Agriculture", "Reefer IoT temperature excursion & post-harvest shelf-life predictor", 0.96, 30),
    ("seedgenius", "Algorise SeedGenius Lab", "Agriculture", "Genotype-by-environment trial plot genetic marker matching", 0.94, 65),

    # Sector 2: Enterprise Operations & B2B HR
    ("nexus_core", "Algorise Nexus Core", "Enterprise", "Autonomous customer support & zero-trust transactional DB action bot", 0.98, 30),
    ("cortex_graphrag", "Algorise Cortex GraphRAG", "Enterprise", "Zero-leakage multi-hop knowledge graph enterprise search brain", 0.99, 45),
    ("hunter_b2b", "Algorise Hunter B2B", "Enterprise", "Autonomous B2B prospect discovery, intent-scoring & outreach engine", 0.95, 50),
    ("pulse_bi", "Algorise Pulse BI", "Enterprise", "Natural language to read-only SQL business intelligence generator", 0.98, 40),
    ("scribe_hr", "Algorise Scribe HR", "Enterprise", "Candidate resume grading, skill benchmarking & interview scheduler", 0.93, 40),
    ("vendoraudit", "Algorise VendorAudit Sentinel", "Enterprise", "Procurement invoice OCR & master service agreement price drift auditor", 0.97, 35),
    ("echo_voice", "Algorise Echo Voice Telephony", "Enterprise", "Sub-300ms WebRTC conversational voice telephony receptionist", 0.96, 25),
    ("onboardflow", "Algorise OnboardFlow", "Enterprise", "Automated employee IT account provisioning & IAM access orchestrator", 0.99, 55),
    ("rfp_responder", "Algorise RFP-Responder", "Enterprise", "Technical RFP proposal drafting engine with proof citations", 0.94, 70),
    ("exitrisk", "Algorise ExitRisk Predictor", "Enterprise", "Privacy-preserving employee burnout & attrition probability monitor", 0.91, 50),

    # Sector 3: Retail & E-Commerce
    ("cartrescue", "Algorise CartRescue Autonomous", "Retail", "Predictive abandoned cart recovery bot with dynamic LTV incentives", 0.94, 30),
    ("shelfvision", "Algorise ShelfVision Edge", "Retail", "CCTV camera real-time out-of-stock & planogram compliance detector", 0.96, 35),
    ("dynamicprice", "Algorise DynamicPrice Matrix", "Retail", "Real-time competitor scraping & margin-optimized dynamic repricing", 0.95, 45),
    ("returnguard", "Algorise ReturnGuard AI", "Retail", "Wardrobing & return fraud detection network analysis bot", 0.97, 30),
    ("stylist_3d", "Algorise Stylist 3D", "Retail", "Multimodal fashion visual recommender & bundle builder", 0.93, 50),
    ("restock_iq", "Algorise RestockIQ ERP", "Retail", "Probabilistic supply-demand replenishing & purchase order drafter", 0.96, 40),
    ("reviewshield", "Algorise ReviewShield", "Retail", "Review sentiment monitoring & automated fake review dispute filer", 0.94, 35),
    ("influencer_roi", "Algorise InfluencerROI", "Retail", "Computer vision social post verification & sales attribution tracker", 0.95, 55),
    ("adspend_allocator", "Algorise AdSpend Allocator", "Retail", "Bayesian multi-touch attribution & real-time ad budget shifter", 0.96, 40),
    ("omnichannel_sync", "Algorise Omnichannel SyncEngine", "Retail", "Sub-second multi-storefront inventory synchronization pipeline", 0.99, 20),

    # Sector 4: Creator Economy & Media
    ("sponsorscout", "Algorise SponsorScout", "Creator", "Inbound brand sponsorship email negotiator & rate card qualifier", 0.93, 40),
    ("viralhook", "Algorise ViralHook Analyzer", "Creator", "Video script retention predictor & viral hook alternative generator", 0.92, 45),
    ("fansync", "Algorise FanSync Omnichannel", "Creator", "Creator voice-cloned comment & DM conversion bot", 0.95, 25),
    ("clipcutter", "Algorise ClipCutter Edge", "Creator", "Multimodal peak energy detector & 9:16 vertical video clipper", 0.94, 60),
    ("trendpulse", "Algorise TrendPulse Radar", "Creator", "Mathematical velocity detector for emerging audio & meme trends", 0.91, 50),
    ("clonevoice", "Algorise CloneVoice Polyglot", "Creator", "Multilingual voice cloning & automated video lip-sync dubbing", 0.96, 65),
    ("rightsguard", "Algorise RightsGuard", "Creator", "Perceptual hashing video piracy detection & automated DMCA filer", 0.98, 40),
    ("contentforge", "Algorise ContentForge Multi-Format", "Creator", "Multi-agent cross-platform content repurposing engine", 0.94, 55),
    ("fantier", "Algorise FanTier Subscriptions", "Creator", "Community engagement decay predictor & failed payment recovery", 0.95, 35),
    ("merchdrop", "Algorise MerchDrop Forecaster", "Creator", "Audience demographic demand model & print-on-demand fulfillment", 0.93, 45),

    # Sector 5: Healthcare & Medical
    ("caretriage", "Algorise CareTriage Clinical", "Healthcare", "HIPAA-compliant 24/7 clinical urgency triage & intake bot", 0.98, 30),
    ("medscribe", "Algorise MedScribe Ambient", "Healthcare", "Ambient doctor-patient consultation listener generating SOAP notes", 0.97, 45),
    ("dentalrecall", "Algorise DentalRecall Autonomous", "Healthcare", "Patient hygiene recall & dormant schedule filler agent", 0.96, 25),
    ("claimguard", "Algorise ClaimGuard RCM", "Healthcare", "Pre-adjudication medical billing code optimizer & denial preventer", 0.99, 40),
    ("pharmacheck", "Algorise PharmaCheck Contraindication", "Healthcare", "Polypharmacy drug-drug interaction & allergy safety checker", 0.999, 20),
    ("postop_monitor", "Algorise PostOp RemoteMonitor", "Healthcare", "Post-surgical recovery check-in bot with nurse emergency alert", 0.98, 25),
    ("priorauth", "Algorise PriorAuth Expediter", "Healthcare", "Automated clinical necessity packet generator for insurance pre-auth", 0.96, 50),
    ("labexplainer", "Algorise LabResult Explainer", "Healthcare", "Biomarker blood panel translation into plain patient explanations", 0.97, 35),
    ("clinicaltrial", "Algorise ClinicalTrial Matcher", "Healthcare", "Patient EHR inclusion/exclusion matching for experimental oncology trials", 0.95, 60),
    ("radassist", "Algorise RadAssist Vision", "Healthcare", "X-ray/CT scan preliminary lesion detection & radiologist triage", 0.98, 45),

    # Sector 6: Real Estate & Property
    ("realtorvoice", "Algorise RealtorVoice 24/7", "RealEstate", "Sub-300ms WebRTC voice agent qualifying property buyer leads", 0.96, 25),
    ("propfix", "Algorise PropFix Dispatch", "RealEstate", "Tenant maintenance photo diagnostic & plumber/electrician dispatch", 0.95, 35),
    ("leasedraft", "Algorise LeaseDraft Compliance", "RealEstate", "State-compliant residential/commercial lease drafting & e-sign bot", 0.98, 40),
    ("compgenius", "Algorise CompGenius CMA", "RealEstate", "Real-time comparable market analysis & property valuation PDF generator", 0.94, 50),
    ("tenantvet", "Algorise TenantVet", "RealEstate", "Credit, income, background & paystub fraud verification scorer", 0.97, 35),
    ("stager_3d", "Algorise Stager 3D", "RealEstate", "Computer vision architectural furniture staging & photo declutterer", 0.95, 55),
    ("buildprogress", "Algorise BuildProgress Drone", "RealEstate", "Construction site drone photogrammetry & milestone verification", 0.96, 60),
    ("energyaudit", "Algorise EnergyAudit ESG", "RealEstate", "Commercial building HVAC/energy telemetry & carbon footprint optimizer", 0.94, 45),
    ("zoningcode", "Algorise ZoningCode Explorer", "RealEstate", "Municipal zoning ordinance RAG & property development entitlement checker", 0.95, 50),
    ("titleaudit", "Algorise TitleAudit Escrow", "RealEstate", "County land deed recording lien search & escrow title packet auditor", 0.98, 45),

    # Sector 7: Banking, Wealth & FinTech
    ("alphaaudit", "Algorise AlphaAudit 10-K", "Finance", "Financial statement footnote discrepancy & off-balance-sheet debt scanner", 0.98, 55),
    ("wealthbot", "Algorise WealthBot Rebalancer", "Finance", "Portfolio drift monitoring & tax-loss harvesting order drafter", 0.97, 40),
    ("loanfast", "Algorise LoanFast Underwriting", "Finance", "Commercial DSCR cash-flow underwriter parsing 24mo bank statements", 0.98, 50),
    ("fraudshield", "Algorise FraudShield Sub-15ms", "Finance", "Sub-15ms credit card transaction anomaly & identity takeover shield", 0.999, 12),
    ("taxextract", "Algorise TaxExtract OCR", "Finance", "W-2, 1099, K-1 precision tax document extractor into CPA formats", 0.98, 40),
    ("expenseaudit", "Algorise ExpenseAudit", "Finance", "Corporate expense receipt policy compliance & fraud auditor", 0.97, 30),
    ("aml_sentinel", "Algorise AML-Sentinel", "Finance", "Anti-money laundering transaction graph clustering & SAR drafter", 0.99, 45),
    ("portfoliostress", "Algorise PortfolioStress Macro", "Finance", "Monte Carlo geopolitical & interest-rate macroeconomic stress-tester", 0.95, 65),
    ("debt_recovery", "Algorise DebtRecovery Empathetic", "Finance", "Conversational empathetic debt settlement & payment plan negotiator", 0.94, 35),
    ("credit_alt", "Algorise CreditScore Alternative", "Finance", "Cash-flow banking transaction scoring for unbanked/thin-file borrowers", 0.96, 40),

    # Sector 8: Legal, Compliance & Cybersecurity
    ("redline_playbook", "Algorise Redline Playbook", "Legal", "Autonomous contract review bot applying firm negotiation playbooks", 0.98, 45),
    ("ediscovery_swarm", "Algorise eDiscovery Swarm", "Legal", "Multi-agent litigation swarm scanning corporate emails for smoking guns", 0.97, 65),
    ("patentscope", "Algorise PatentScope", "Legal", "USPTO/EPO global patent prior-art embedding search & infringement scorer", 0.95, 55),
    ("gdprguard", "Algorise GDPRGuard Continuous", "Legal", "Continuous website & database PII storage regulatory compliance auditor", 0.98, 40),
    ("intakelegal", "Algorise IntakeLegal Injury", "Legal", "24/7 personal injury claim qualification & retainer e-sign bot", 0.96, 30),
    ("courtdocket", "Algorise CourtDocket Predictor", "Legal", "Judicial ruling prediction model & court deadline calendaring agent", 0.94, 45),
    ("ma_diligence", "Algorise M&A DiligenceRoom", "Legal", "M&A virtual data room material contract risk & change-of-control extractor", 0.97, 70),
    ("policydrift", "Algorise PolicyDrift Regulatory", "Legal", "Federal register & regulatory amendment impact scanner for corporate policy", 0.96, 50),
    ("trademarkwatch", "Algorise IP-Trademark Watch", "Legal", "Global trademark registry phonetic & visual similarity infringement scanner", 0.95, 40),
    ("sanctionscheck", "Algorise SanctionsCheck Global", "Legal", "OFAC, EU, UN real-time sanctions screening & PEP compliance gateway", 0.999, 15),

    # Sector 9: Logistics, Supply Chain & Fleet
    ("routeoptima", "Algorise RouteOptima Fleet", "Logistics", "Genetic multi-stop delivery vehicle route optimization engine", 0.97, 45),
    ("freightbroker", "Algorise FreightBroker Spot", "Logistics", "Autonomous freight load-matching & carrier spot-rate negotiator", 0.95, 40),
    ("bol_extract", "Algorise BOL-Extract Customs", "Logistics", "Bill of Lading & customs shipping document OCR ingestion pipeline", 0.98, 35),
    ("fleetwatch", "Algorise FleetWatch Telematics", "Logistics", "OBD-II vehicle telematics predictive engine breakdown detector", 0.96, 30),
    ("portdelay", "Algorise PortDelay Congestion", "Logistics", "AIS vessel radar & ocean container port congestion predictor", 0.94, 50),
    ("warehouseslotting", "Algorise WarehouseSlotting 3D", "Logistics", "Forklift pick-path optimizer & fast-moving inventory slotting engine", 0.96, 45),
    ("coldchain_pharma", "Algorise ColdChain Pharma", "Logistics", "Biologics & vaccine thermal stability monitor with GDP compliance audit", 0.99, 25),
    ("lastmile_geofence", "Algorise LastMile Geofence", "Logistics", "Customer proximity SMS dispatch & proof-of-delivery photo validator", 0.97, 25),
    ("driversafety", "Algorise DriverSafety Cam", "Logistics", "In-cab computer vision driver fatigue & distraction alert agent", 0.98, 20),
    ("container_repo", "Algorise ContainerReposition", "Logistics", "Global empty shipping container repositioning cost-minimization solver", 0.93, 60),

    # Sector 10: Education, EdTech & Research
    ("tutoriq", "Algorise TutorIQ Socratic", "Education", "Socratic 24/7 personalized homework tutor guiding students without giving answers", 0.95, 30),
    ("gradeassure", "Algorise GradeAssure Essay", "Education", "Automated essay & short-answer grading engine with rubric feedback", 0.94, 40),
    ("admitguide", "Algorise AdmitGuide International", "Education", "University admissions inquiry counselor & foreign credential auditor", 0.95, 35),
    ("syllabusgen", "Algorise SyllabusGen Accredited", "Education", "12-week accredited course curriculum, slide deck & exam bank generator", 0.93, 50),
    ("dropoutwatch", "Algorise DropoutWatch Retention", "Education", "LMS student engagement anomaly model alerting academic advisors early", 0.96, 35),
    ("examproctor", "Algorise ExamProctor Vision", "Education", "Real-time webcam gaze & second-monitor anti-cheat proctoring bot", 0.97, 25),
    ("adaptivemath", "Algorise AdaptiveLearning Math", "Education", "Dynamic STEM knowledge-space mastery graph engine with personalized pacing", 0.96, 30),
    ("researchlit", "Algorise ResearchLit Synthesis", "Education", "10,000-paper scientific literature meta-analysis & methodology comparative RAG", 0.97, 65),
    ("skillmatrix", "Algorise CorporateSkill Matrix", "Education", "Enterprise employee skill gap analysis & personalized upskilling paths", 0.94, 45),
    ("grantscout", "Algorise GrantScout Academic", "Education", "NIH/NSF research grant RFP matching & initial grant proposal drafter", 0.93, 60)
]

HERO_BOT_REGISTRY_MAP: Dict[str, tuple] = {b[0]: b for b in HERO_BOT_DEFINITIONS}
HERO_BOT_IDS_SET = set(HERO_BOT_REGISTRY_MAP.keys())


class HeroBotRunner:
    def __init__(self):
        self.safety_gate = AlgoriseSafetyGate()
        self.graph_rag = AlgoriseGraphRAG()
        # Seed GraphRAG with baseline enterprise entities
        self.graph_rag.index_entity_relations("enterprise_sla", ["uptime_9999", "tier1_support", "vpc_peering"], {"status": "ACTIVE"})
        self.graph_rag.index_entity_relations("compliance", ["hipaa_certified", "soc2_type2", "gdpr_compliant"], {"status": "VERIFIED"})

    def _cache_key(self, bot_id: str, input_payload: Dict[str, Any]) -> str:
        """Generate cache key for bot execution."""
        payload_str = json.dumps(input_payload, sort_keys=True, default=str)
        input_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
        return CacheKeys.bot_execution(bot_id, input_hash)

    async def execute_hero_bot_cached(self, bot_id: str, input_payload: Dict[str, Any], tuned_params: Optional[Dict[str, Any]] = None) -> BotResult:
        """Execute hero bot with Redis caching."""
        cache_key = self._cache_key(bot_id, input_payload)
        
        # Try cache first
        cached = await redis_manager.get(cache_key)
        if cached is not None:
            cached["cache_hit"] = True
            return BotResult(
                task_id=input_payload.get("task_id", f"task_{bot_id}"),
                bot_name=cached.get("product_name", bot_id),
                success=True,
                data=cached,
                reasoning_trace=[f"[{bot_id}] Cache HIT"],
                latency_ms=0.01,
            )

        # Execute normally (using sync version for compatibility)
        result = self.execute_hero_bot(bot_id, input_payload, tuned_params)
        
        # Cache successful results
        if result.success:
            cache_data = result.data.copy()
            cache_data["cache_hit"] = False
            await redis_manager.set(cache_key, cache_data, expire=3600)
        
        return result

    def execute_hero_bot(self, bot_id: str, input_payload: Dict[str, Any], tuned_params: Optional[Dict[str, Any]] = None) -> BotResult:
        start_time = time.time()
        
        # Locate definition via O(1) hash map
        matched = HERO_BOT_REGISTRY_MAP.get(bot_id)
        if not matched:
            raise ValueError(f"Bot '{bot_id}' not found in Algorise Hero Registry.")
        
        b_id, name, sector, desc, base_conf, target_latency = matched
        params = tuned_params or {}
        confidence_boost = params.get("confidence_boost", 0.0)
        target_conf = min(0.999, base_conf + confidence_boost)
        
        trace = [f"[{name}] Ingested task payload for sector '{sector}'"]

        # 1. Deterministic Causal Safety Audit
        action_intent = input_payload.get("proposed_action", {"action": "standard_execution", "target": bot_id})
        is_safe, safety_code, audit_flags = self.safety_gate.audit_bot_action(b_id, action_intent)
        trace.append(f"[{name}] Causal Safety Gate: {safety_code} (Passed: {is_safe})")

        if not is_safe:
            return BotResult(
                task_id=input_payload.get("task_id", "sim_task"),
                bot_name=name,
                success=False,
                data={"error": "Causal Safety Blocked", "flags": audit_flags},
                reasoning_trace=trace,
                latency_ms=round((time.time() - start_time) * 1000, 2)
            )

        # 2. Context Grounding (GraphRAG)
        query = input_payload.get("query", desc)
        context_res = self.graph_rag.query_context_sync(query)
        trace.append(f"[{name}] GraphRAG Context: density score = {context_res['context_density_score']}")

        # 3. Real Domain Algorithmic Execution
        from .hero_algorithms import execute_algorithmic_domain_bot
        domain_result = execute_algorithmic_domain_bot(b_id, sector, input_payload)
        trace.append(f"[{name}] Computed domain algorithm for '{sector}'. Result keys: {list(domain_result.keys())}")
        
        output_payload = {
            "bot_id": b_id,
            "product_name": name,
            "sector": sector,
            "status": "SUCCESS",
            "confidence_score": max(target_conf, domain_result.get("confidence", target_conf)),
            "domain_output": domain_result,
            "context_nodes": len(context_res["retrieved_context_nodes"]),
            "safety_clearance": safety_code
        }

        latency = round((time.time() - start_time) * 1000, 2)
        trace.append(f"[{name}] Execution completed in {latency}ms (target <= {target_latency}ms)")

        return BotResult(
            task_id=input_payload.get("task_id", f"task_{b_id}"),
            bot_name=name,
            success=True,
            data=output_payload,
            reasoning_trace=trace,
            latency_ms=latency
        )
