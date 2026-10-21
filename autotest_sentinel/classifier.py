"""
AutoTest Sentinel: Bayesian & Statistical Flakiness Classifier
Identifies non-deterministic test failures by evaluating execution variance,
timing jitter, and error trace signatures.
"""

import math
import re
from typing import Dict, List, Optional

from .models import (
    FlakeCategory,
    FlakinessReport,
    RootCauseHypothesis,
    TestExecutionRecord,
    TestStatus,
)


class FlakeClassifier:
    """
    Statistical and Bayesian classifier for non-deterministic test behavior.
    """

    # Regex signatures for known transient error domains
    TIMING_PATTERNS = [
        re.compile(r"timeout(error)?", re.IGNORECASE),
        re.compile(r"timed\s+out", re.IGNORECASE),
        re.compile(r"deadline\s+exceeded", re.IGNORECASE),
        re.compile(r"asyncio\..*timeout", re.IGNORECASE),
        re.compile(r"wait_until.*exceeded", re.IGNORECASE),
    ]

    NETWORK_PATTERNS = [
        re.compile(r"connection(refused|reset)error", re.IGNORECASE),
        re.compile(r"max\s+retries\s+exceeded", re.IGNORECASE),
        re.compile(r"remote\s+end\s+closed\s+connection", re.IGNORECASE),
        re.compile(r"temporary\s+failure\s+in\s+name\s+resolution", re.IGNORECASE),
    ]

    SHARED_STATE_PATTERNS = [
        re.compile(r"database\s+is\s+locked", re.IGNORECASE),
        re.compile(r"lock\s+wait\s+timeout", re.IGNORECASE),
        re.compile(r"deadlock\s+detected", re.IGNORECASE),
        re.compile(r"unique\s+constraint.*violated", re.IGNORECASE),
        re.compile(r"already\s+exists", re.IGNORECASE),
    ]

    PORT_PATTERNS = [
        re.compile(r"address\s+already\s+in\s+use", re.IGNORECASE),
        re.compile(r"errno\s+(98|10048)", re.IGNORECASE),
    ]

    def __init__(self, prior_flakiness: float = 0.05):
        self.prior_flakiness = prior_flakiness

    def analyze_executions(self, records: List[TestExecutionRecord]) -> FlakinessReport:
        """
        Takes a list of execution records for a single test_id and returns
        a comprehensive FlakinessReport.
        """
        if not records:
            raise ValueError("Execution records list cannot be empty.")

        test_id = records[0].test_id
        file_path = records[0].file_path
        total_runs = len(records)

        passed_runs = sum(1 for r in records if r.status == TestStatus.PASSED)
        failed_runs = sum(1 for r in records if r.status == TestStatus.FAILED)
        skipped_runs = sum(1 for r in records if r.status == TestStatus.SKIPPED)

        effective_runs = passed_runs + failed_runs
        if effective_runs == 0:
            return FlakinessReport(
                test_id=test_id,
                file_path=file_path,
                flakiness_score=0.0,
                category=FlakeCategory.LOW_CONFIDENCE,
                root_cause=RootCauseHypothesis.UNKNOWN,
                total_runs=total_runs,
                failure_rate=0.0,
                duration_jitter=0.0,
                recommended_action="OBSERVE",
                remediation_notes="All recorded runs were skipped.",
            )

        failure_rate = failed_runs / effective_runs

        # Calculate duration stats (mean and standard deviation)
        durations = [r.duration_seconds for r in records if r.duration_seconds > 0]
        if durations:
            mean_dur = sum(durations) / len(durations)
            if len(durations) > 1 and mean_dur > 0:
                variance = sum((d - mean_dur) ** 2 for d in durations) / (len(durations) - 1)
                std_dev = math.sqrt(variance)
                duration_jitter = std_dev / mean_dur
            else:
                duration_jitter = 0.0
        else:
            duration_jitter = 0.0

        # Examine error signatures
        root_cause = self._identify_root_cause(records)

        # Compute Bayesian Posterior Probability: P(Flaky | Evidence)
        flakiness_score = self._compute_bayesian_posterior(
            effective_runs=effective_runs,
            passed_runs=passed_runs,
            failed_runs=failed_runs,
            duration_jitter=duration_jitter,
            root_cause=root_cause,
        )

        # Categorize
        if effective_runs < 3:
            category = FlakeCategory.LOW_CONFIDENCE
        elif flakiness_score >= 0.75:
            category = FlakeCategory.FLAKY_HIGH
        elif flakiness_score >= 0.40:
            category = FlakeCategory.FLAKY_MEDIUM
        elif failure_rate == 1.0:
            category = FlakeCategory.DETERMINISTIC_FAIL
        else:
            category = FlakeCategory.DETERMINISTIC_PASS

        # Recommended Action
        if category == FlakeCategory.FLAKY_HIGH:
            recommended_action = "QUARANTINE"
            notes = (
                f"High flakiness confidence ({flakiness_score:.2f}). "
                f"Intermittent pass/fail detected across identical code base. Root cause: {root_cause.value}."
            )
        elif category == FlakeCategory.FLAKY_MEDIUM:
            recommended_action = "AUTO_HEAL"
            notes = (
                f"Moderate flakiness detected ({flakiness_score:.2f}). Recommend AST inspection and retry dampening."
            )
        elif category == FlakeCategory.DETERMINISTIC_FAIL:
            recommended_action = "IGNORE"
            notes = "Test fails 100% deterministically. True regression, do not quarantine."
        else:
            recommended_action = "NONE"
            notes = "Test passes reliably."

        return FlakinessReport(
            test_id=test_id,
            file_path=file_path,
            flakiness_score=flakiness_score,
            category=category,
            root_cause=root_cause,
            total_runs=total_runs,
            failure_rate=failure_rate,
            duration_jitter=duration_jitter,
            recommended_action=recommended_action,
            remediation_notes=notes,
        )

    def _identify_root_cause(self, records: List[TestExecutionRecord]) -> RootCauseHypothesis:
        """Inspects failure traces across runs to infer probable root cause."""
        error_blob = " ".join(
            (r.error_message or "") + " " + (r.stack_trace or "")
            for r in records
            if r.status == TestStatus.FAILED
        )

        if not error_blob.strip():
            return RootCauseHypothesis.UNKNOWN

        for pattern in self.TIMING_PATTERNS:
            if pattern.search(error_blob):
                return RootCauseHypothesis.TIMING_RACE

        for pattern in self.PORT_PATTERNS:
            if pattern.search(error_blob):
                return RootCauseHypothesis.ENVIRONMENT_COLLISION

        for pattern in self.SHARED_STATE_PATTERNS:
            if pattern.search(error_blob):
                return RootCauseHypothesis.SHARED_STATE

        for pattern in self.NETWORK_PATTERNS:
            if pattern.search(error_blob):
                return RootCauseHypothesis.NETWORK_IO

        return RootCauseHypothesis.UNKNOWN

    def evaluate_jitter(self, durations: List[float], threshold: float = 0.35) -> bool:
        """Evaluates timing jitter using coefficient of variation."""
        if not durations or len(durations) < 2:
            return False
        mean_dur = sum(durations) / len(durations)
        if mean_dur <= 0:
            return False
        variance = sum((d - mean_dur) ** 2 for d in durations) / (len(durations) - 1)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_dur
        return cv > threshold

    def scan_anti_patterns(self, code: str) -> List[str]:
        """Scans source code for common flakiness anti-patterns."""
        patterns_found = []
        if re.search(r'time\.sleep\s*\(', code):
            patterns_found.append('FIXED_SLEEP')
        if re.search(r'random\.(randint|random|uniform|choice)\s*\(', code):
            patterns_found.append('UNSEEDED_RANDOM')
        if re.search(r'threading\.Thread', code):
            patterns_found.append('NON_DETERMINISTIC_THREADING')
        if re.search(r'multiprocessing\.', code):
            patterns_found.append('NON_DETERMINISTIC_MULTIPROCESSING')
        if re.search(r'asyncio\.sleep', code):
            patterns_found.append('ASYNC_SLEEP')
        if re.search(r'requests\.(get|post|put|delete)', code) and 'timeout=' not in code:
            patterns_found.append('HTTP_NO_TIMEOUT')
        return patterns_found

    def _compute_bayesian_posterior(
        self,
        effective_runs: int,
        passed_runs: int,
        failed_runs: int,
        duration_jitter: float,
        root_cause: RootCauseHypothesis,
    ) -> float:
        """
        Computes P(Flaky | Observation).
        Observation contains:
        1. Both passes and failures observed on identical commits.
        2. High timing jitter (CV > 0.35).
        3. Transient error signatures (Timeout, Race, Collision).
        """
        # If all passed or all failed in a small sample:
        if passed_runs == effective_runs:
            return 0.01  # negligible
        if failed_runs == effective_runs:
            # Deterministic bug has high prior probability (0.95 vs 0.05 flaky)
            return 0.05

        # If we see BOTH passes and failures in the sample:
        # A truly deterministic test cannot flip outcomes on identical commits.
        # Under Flaky hypothesis, observing alternating outcomes is expected (~0.85+).
        # Under Deterministic hypothesis, observing conflicting outcomes decays exponentially.
        p_data_given_flaky = 0.92
        p_data_given_deterministic = max(0.0005, 0.05 ** min(passed_runs, failed_runs))

        # Bonus evidence for timing jitter and transient root causes
        if duration_jitter > 0.35:
            p_data_given_flaky = min(0.99, p_data_given_flaky * 1.1)
        if root_cause in (
            RootCauseHypothesis.TIMING_RACE,
            RootCauseHypothesis.ENVIRONMENT_COLLISION,
            RootCauseHypothesis.SHARED_STATE,
        ):
            p_data_given_flaky = min(0.995, p_data_given_flaky * 1.15)

        prior_f = self.prior_flakiness
        prior_not_f = 1.0 - prior_f

        numerator = p_data_given_flaky * prior_f
        denominator = (p_data_given_flaky * prior_f) + (p_data_given_deterministic * prior_not_f)

        if denominator <= 0:
            return 0.50

        posterior = numerator / denominator

        # Scale with sample size confidence:
        confidence_multiplier = min(1.0, math.sqrt(effective_runs) / 2.0)
        final_score = posterior * confidence_multiplier + (1 - confidence_multiplier) * 0.5

        # Normalize score strictly to [0.0, 1.0]
        return round(max(0.0, min(1.0, final_score)), 4)
