"""
TraceRoot AI: Git Blame & Commit Bisector
Maps failing stack frames to the exact Git commit, author, and revision history.
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional

from .models import BlameContext, IncidentPayload, StackFrame


class BlameAnalyzer:
    """
    Correlates incident stack frames with Git blame metadata.
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)

    def analyze_culprit_frame(
        self, payload: IncidentPayload
    ) -> Optional[BlameContext]:
        """Finds the most specific internal frame and extracts Git blame telemetry."""
        internal_frames = [f for f in payload.frames if f.is_internal]
        if not internal_frames:
            return None

        # Culprit frame is typically the deepest internal application frame
        culprit = internal_frames[-1]

        rel_path = culprit.file_path
        if os.path.isabs(rel_path):
            rel_path = os.path.relpath(rel_path, self.root_dir).replace("\\", "/")

        line_no = culprit.line_number
        full_path = os.path.join(self.root_dir, rel_path)

        commit_sha = "unknown"
        author = "unknown"
        commit_date = "unknown"
        summary = "unknown"

        if os.path.exists(full_path):
            try:
                cmd = ["git", "blame", "-L", f"{line_no},{line_no}", "--porcelain", rel_path]
                res = subprocess.run(
                    cmd, cwd=self.root_dir, capture_output=True, text=True, check=True
                )
                lines = res.stdout.splitlines()
                if lines:
                    commit_sha = lines[0].split()[0]
                    for l in lines:
                        if l.startswith("author "):
                            author = l[len("author "):]
                        elif l.startswith("summary "):
                            summary = l[len("summary "):]
                        elif l.startswith("author-time "):
                            commit_date = l[len("author-time "):]
            except Exception:
                pass

        surrounding_lines = []
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    file_lines = f.readlines()
                start = max(0, line_no - 4)
                end = min(len(file_lines), line_no + 3)
                surrounding_lines = [
                    f"{idx+1}: {file_lines[idx].rstrip()}" for idx in range(start, end)
                ]
            except Exception:
                pass

        return BlameContext(
            file_path=rel_path,
            line_number=line_no,
            culprit_commit_sha=commit_sha,
            author_name=author,
            commit_date=commit_date,
            commit_summary=summary,
            failing_function=culprit.function_name,
            surrounding_code="\n".join(surrounding_lines),
        )
