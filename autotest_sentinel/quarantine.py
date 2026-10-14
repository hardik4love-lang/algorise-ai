"""
AutoTest Sentinel: Quarantine Manager
Manages declarative test quarantine manifests, isolates non-deterministic tests,
and generates GitHub Actions step annotations.
"""
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Dict, List, Optional
from .models import FlakinessReport, QuarantineManifest

class QuarantineManager:
    """
    Handles isolation of flaky tests to unblock CI merge gates
    while preserving test failure visibility.
    """
    DEFAULT_MANIFEST_PATH = os.path.join('.autotest', 'quarantine.json')

    def __init__(self, manifest_path: Optional[str]=None):
        self.manifest_path = manifest_path or self.DEFAULT_MANIFEST_PATH
        self.manifest = self._load_or_create_manifest()

    def _load_or_create_manifest(self) -> QuarantineManifest:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return QuarantineManifest(version=data.get('version', '1.0.0'), updated_at=data.get('updated_at', datetime.now(timezone.utc).isoformat()), quarantined_tests=data.get('quarantined_tests', {}))
            except Exception:
                pass
        return QuarantineManifest()

    def save_manifest(self) -> None:
        """Persists the quarantine state to disk."""
        directory = os.path.dirname(self.manifest_path)
        if directory and (not os.path.exists(directory)):
            os.makedirs(directory, exist_ok=True)
        self.manifest.updated_at = datetime.now(timezone.utc).isoformat()
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump({'version': self.manifest.version, 'updated_at': self.manifest.updated_at, 'quarantined_tests': self.manifest.quarantined_tests}, f, indent=2)

    def quarantine_test(self, report: FlakinessReport, reason: Optional[str]=None, ttl_days: int=14) -> bool:
        """
        Adds a test to the quarantine registry with an expiration TTL.
        Returns True if newly added, False if already present.
        """
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=ttl_days)).isoformat()
        entry = {'test_id': report.test_id, 'file_path': report.file_path, 'flakiness_score': report.flakiness_score, 'root_cause': report.root_cause.value, 'failure_rate': round(report.failure_rate, 4), 'reason': reason or report.remediation_notes, 'quarantined_at': now.isoformat(), 'expires_at': expires_at}
        is_new = report.test_id not in self.manifest.quarantined_tests
        self.manifest.quarantined_tests[report.test_id] = entry
        self.save_manifest()
        return is_new

    def unquarantine_test(self, test_id: str) -> bool:
        """Removes a test from quarantine once healed."""
        if test_id in self.manifest.quarantined_tests:
            del self.manifest.quarantined_tests[test_id]
            self.save_manifest()
            return True
        return False

    def is_quarantined(self, test_id: str) -> bool:
        """Checks if a test is currently quarantined and has not expired."""
        if test_id not in self.manifest.quarantined_tests:
            return False
        entry = self.manifest.quarantined_tests[test_id]
        expires_at_str = entry.get('expires_at')
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) > expires_at:
                    del self.manifest.quarantined_tests[test_id]
                    self.save_manifest()
                    return False
            except ValueError:
                pass
        return True

    def get_quarantined_ids(self) -> List[str]:
        """Returns all currently active quarantined test IDs."""
        return [tid for tid in list(self.manifest.quarantined_tests.keys()) if self.is_quarantined(tid)]

    def generate_pytest_deselection_args(self) -> List[str]:
        """
        Generates pytest command-line arguments to deselect quarantined tests.
        Example: ['--deselect', 'tests/test_foo.py::test_flaky']
        """
        args = []
        for tid in self.get_quarantined_ids():
            args.extend(['--deselect', tid])
        return args

    def emit_github_actions_annotations(self) -> List[str]:
        """
        Generates GitHub Actions workflow commands to annotate quarantined tests
        directly on the GitHub pull request / run page.
        """
        annotations = []
        for tid, entry in self.manifest.quarantined_tests.items():
            file_path = entry.get('file_path', '')
            reason = entry.get('reason', 'Flaky behavior detected')
            score = entry.get('flakiness_score', 0.0)
            msg = f'::warning file={file_path},title=Flaky Test Quarantined ({tid})::AutoTest Sentinel isolated this test (Flakiness Score: {score}). Reason: {reason}'
            annotations.append(msg)
        return annotations
