"""
Tests for the Job Placement Ecosystem (dual-sided marketplace, $1/month subscription).
"""

import os
import tempfile
import pytest

from job_portal.models import (
    EmploymentType,
    JobPosting,
    SubscriptionStatus,
    WorkerProfile,
)
from job_portal.matching_engine import JobMatchingEngine
from job_portal.service import MarketplaceService, SUBSCRIPTION_FEE_USD


@pytest.fixture
def service():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield MarketplaceService(data_dir=tmpdir)


class TestModels:
    """Tests for the marketplace data models."""

    def test_subscription_fee_is_one_dollar(self):
        assert SUBSCRIPTION_FEE_USD == 1.00

    def test_job_posting_defaults(self):
        posting = JobPosting(
            vacancy_id="vac_1",
            employer_id="emp_1",
            title="Senior DevEx Engineer",
            description="Build CI automation",
        )
        assert posting.active is True
        assert posting.sponsored is False
        assert posting.employment_type == EmploymentType.FULL_TIME
        assert posting.required_skills == []

    def test_worker_profile_defaults(self):
        worker = WorkerProfile(
            worker_id="w1",
            github_handle="octocat",
        )
        assert worker.subscription_status == SubscriptionStatus.ACTIVE
        assert worker.subscription_fee_usd == 1.00
        assert worker.verified_benchmark_score == 0.0


class TestMatchingEngine:
    """Tests for the AI job matching engine."""

    def test_perfect_skill_match(self):
        engine = JobMatchingEngine()
        vacancy = JobPosting(
            vacancy_id="v1",
            employer_id="e1",
            title="DevEx Engineer",
            description="d",
            required_skills=["python", "ast"],
        )
        worker = WorkerProfile(
            worker_id="w1",
            github_handle="gh",
            skills=["python", "ast"],
            verified_benchmark_score=100.0,
        )
        match = engine.calculate_match(vacancy, worker)
        assert match.match_score == 1.0
        assert set(match.matched_skills) == {"python", "ast"}

    def test_no_skill_overlap_low_score(self):
        engine = JobMatchingEngine()
        vacancy = JobPosting(
            vacancy_id="v1",
            employer_id="e1",
            title="Rust Engineer",
            description="d",
            required_skills=["rust", "cargo"],
        )
        worker = WorkerProfile(
            worker_id="w1",
            github_handle="gh",
            skills=["python"],
            verified_benchmark_score=0.0,
        )
        match = engine.calculate_match(vacancy, worker)
        assert match.match_score < 0.2
        assert match.matched_skills == []

    def test_partial_overlap(self):
        engine = JobMatchingEngine()
        vacancy = JobPosting(
            vacancy_id="v1",
            employer_id="e1",
            title="Eng",
            description="d",
            required_skills=["python", "rust", "go"],
        )
        worker = WorkerProfile(
            worker_id="w1",
            github_handle="gh",
            skills=["python", "go"],
            verified_benchmark_score=50.0,
        )
        match = engine.calculate_match(vacancy, worker)
        # 2/3 skill overlap * 0.7 + 0.5 * 0.3 = 0.4667 + 0.15 = 0.6167
        assert 0.6 < match.match_score < 0.63

    def test_case_insensitive_matching(self):
        engine = JobMatchingEngine()
        vacancy = JobPosting(
            vacancy_id="v1",
            employer_id="e1",
            title="Eng",
            description="d",
            required_skills=["Python"],
        )
        worker = WorkerProfile(
            worker_id="w1",
            github_handle="gh",
            skills=["python"],
        )
        match = engine.calculate_match(vacancy, worker)
        assert "python" in match.matched_skills

    def test_find_best_matches_sorted_and_limited(self):
        engine = JobMatchingEngine()
        vacancy = JobPosting(
            vacancy_id="v1",
            employer_id="e1",
            title="Eng",
            description="d",
            required_skills=["python"],
        )
        workers = [
            WorkerProfile(worker_id="w1", github_handle="a", skills=["python"], verified_benchmark_score=90.0),
            WorkerProfile(worker_id="w2", github_handle="b", skills=["java"], verified_benchmark_score=99.0),
            WorkerProfile(worker_id="w3", github_handle="c", skills=["python"], verified_benchmark_score=50.0),
        ]
        matches = engine.find_best_matches(vacancy, workers, top_n=2)
        assert len(matches) == 2
        assert matches[0].match_score >= matches[1].match_score
        assert matches[0].worker_id == "w1"

    def test_inactive_subscribers_excluded_from_matching(self):
        engine = JobMatchingEngine()
        vacancy = JobPosting(
            vacancy_id="v1",
            employer_id="e1",
            title="Eng",
            description="d",
            required_skills=["python"],
        )
        workers = [
            WorkerProfile(
                worker_id="w1",
                github_handle="a",
                skills=["python"],
                verified_benchmark_score=100.0,
                subscription_status=SubscriptionStatus.CANCELED,
            ),
        ]
        matches = engine.find_best_matches(vacancy, workers)
        assert len(matches) == 0


class TestMarketplaceService:
    """Tests for the marketplace service (employer + worker sides)."""

    def test_post_vacancy(self, service):
        vacancy = service.post_vacancy(
            employer_id="emp_acme",
            title="Senior DevEx Engineer",
            description="Own the AST analysis platform",
            required_skills=["python", "ast"],
            salary_range_usd="$180k-220k",
        )
        assert vacancy.vacancy_id.startswith("vac_")
        assert vacancy.employer_id == "emp_acme"
        assert len(service.list_vacancies()) == 1

    def test_register_worker_activates_subscription(self, service):
        worker = service.register_worker(
            worker_id="w_dev",
            github_handle="devuser",
            skills=["python"],
            verified_benchmark_score=92.0,
        )
        assert worker.subscription_status == SubscriptionStatus.ACTIVE
        assert worker.subscription_fee_usd == 1.00
        assert len(service.list_workers(active_only=True)) == 1

    def test_renew_subscription_updates_date(self, service):
        service.register_worker("w1", "gh", ["python"])
        before = service.list_workers()[0].last_billing_date
        worker = service.renew_subscription("w1")
        assert worker.subscription_status == SubscriptionStatus.ACTIVE
        assert worker.last_billing_date >= before

    def test_renew_unknown_worker_raises(self, service):
        with pytest.raises(KeyError):
            service.renew_subscription("nope")

    def test_cancel_subscription_deactivates(self, service):
        service.register_worker("w1", "gh", ["python"])
        worker = service.cancel_subscription("w1")
        assert worker.subscription_status == SubscriptionStatus.CANCELED
        assert len(service.list_workers(active_only=True)) == 0

    def test_match_vacancy_returns_ranked_matches(self, service):
        vacancy = service.post_vacancy(
            employer_id="emp1",
            title="AST Engineer",
            description="d",
            required_skills=["ast", "python"],
        )
        service.register_worker("w1", "gh1", ["ast", "python"], verified_benchmark_score=95.0)
        service.register_worker("w2", "gh2", ["cobol"], verified_benchmark_score=99.0)

        matches = service.match_vacancy(vacancy.vacancy_id, top_n=5)
        assert len(matches) == 1
        assert matches[0].worker_id == "w1"
        assert matches[0].match_score > 0.8

    def test_match_nonexistent_vacancy_raises(self, service):
        with pytest.raises(KeyError):
            service.match_vacancy("vac_missing")

    def test_worker_matches_retrieval(self, service):
        vacancy = service.post_vacancy(
            employer_id="emp1",
            title="Eng",
            description="d",
            required_skills=["python"],
        )
        service.register_worker("w1", "gh1", ["python"], verified_benchmark_score=88.0)
        service.match_vacancy(vacancy.vacancy_id)
        matches = service.get_worker_matches("w1")
        assert len(matches) == 1
        assert matches[0].worker_id == "w1"

    def test_revenue_report_mrr(self, service):
        for i in range(10):
            service.register_worker(f"w{i}", f"gh{i}", ["python"])
        report = service.revenue_report()
        assert report["active_subscribers"] == 10
        assert report["mrr_usd"] == 10.00
        assert report["arr_run_rate_usd"] == 120.00
        assert report["gross_margin_pct"] > 0

    def test_revenue_report_after_cancel(self, service):
        service.register_worker("w1", "gh1", ["python"])
        service.cancel_subscription("w1")
        report = service.revenue_report()
        assert report["active_subscribers"] == 0
        assert report["mrr_usd"] == 0.0

    def test_duplicate_registration_replaces(self, service):
        service.register_worker("w1", "gh1", ["python"])
        service.register_worker("w1", "gh1_updated", ["rust"])
        workers = service.list_workers()
        assert len(workers) == 1
        assert workers[0].github_handle == "gh1_updated"


class TestMarketplaceAPI:
    """Integration tests for the marketplace HTTP API."""

    def setup_method(self):
        from fastapi.testclient import TestClient
        from devex.api import app
        self._tmp = tempfile.TemporaryDirectory()
        import job_portal.api as api_module
        api_module._service = MarketplaceService(data_dir=self._tmp.name)
        self.client = TestClient(app)

    def teardown_method(self):
        self._tmp.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/v1/marketplace/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["subscription_fee_usd"] == 1.00

    def test_employer_posts_vacancy(self):
        response = self.client.post(
            "/v1/marketplace/vacancies",
            json={
                "title": "Platform Engineer",
                "description": "Run the AST platform",
                "required_skills": ["python", "ast"],
            },
            headers={"X-Employer-ID": "emp_acme"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["employer_id"] == "emp_acme"
        assert data["active"] is True

    def test_employer_id_header_required(self):
        response = self.client.post(
            "/v1/marketplace/vacancies",
            json={"title": "T", "description": "D"},
        )
        assert response.status_code == 422

    def test_worker_registers_and_renews(self):
        response = self.client.post(
            "/v1/marketplace/workers",
            json={
                "worker_id": "w1",
                "github_handle": "octocat",
                "skills": ["python"],
                "verified_benchmark_score": 91.0,
            },
        )
        assert response.status_code == 201
        assert response.json()["subscription_status"] == "active"

        renew = self.client.post("/v1/marketplace/workers/w1/renew")
        assert renew.status_code == 200
        assert renew.json()["subscription_fee_usd"] == 1.00

    def test_cancel_subscription_endpoint(self):
        self.client.post(
            "/v1/marketplace/workers",
            json={"worker_id": "w1", "github_handle": "gh", "skills": []},
        )
        response = self.client.post("/v1/marketplace/workers/w1/cancel")
        assert response.status_code == 200
        assert response.json()["subscription_status"] == "canceled"

    def test_matching_endpoint(self):
        vacancy = self.client.post(
            "/v1/marketplace/vacancies",
            json={
                "title": "AST Engineer",
                "description": "d",
                "required_skills": ["ast"],
            },
            headers={"X-Employer-ID": "emp1"},
        ).json()

        self.client.post(
            "/v1/marketplace/workers",
            json={
                "worker_id": "w1",
                "github_handle": "gh1",
                "skills": ["ast"],
                "verified_benchmark_score": 95.0,
            },
        )

        response = self.client.post(
            f"/v1/marketplace/vacancies/{vacancy['vacancy_id']}/match"
        )
        assert response.status_code == 200
        matches = response.json()["matches"]
        assert len(matches) == 1
        assert matches[0]["worker_id"] == "w1"

    def test_metrics_endpoint(self):
        self.client.post(
            "/v1/marketplace/workers",
            json={"worker_id": "w1", "github_handle": "gh", "skills": []},
        )
        response = self.client.get("/v1/marketplace/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["active_subscribers"] == 1
        assert data["mrr_usd"] == 1.00
        assert data["arr_run_rate_usd"] == 12.00

    def test_vacancy_404_on_unknown_match(self):
        response = self.client.post("/v1/marketplace/vacancies/vac_missing/match")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
