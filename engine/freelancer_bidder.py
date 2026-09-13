"""
Algorise Freelancer Automated Bidding Engine
Linked to Hardik's verified Freelancer account: hardikk441 (User ID: 94742340)
Handles both:
1. 1-Click Manual Bid Package generation with tailored proposals and runnable code deliverables.
2. 100% Autonomous Headless Auto-Bidding via Freelancer.com REST API (POST /api/projects/0.1/bids/).
"""

import os
import json
import socket
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional

# Enforce IPv4 on Windows to prevent dual-stack DNS timeouts
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

HARDIK_PROFILE = {
    "user_id": 94742340,
    "username": "hardikk441",
    "display_name": "Hardik",
    "profile_url": "https://www.freelancer.in/u/hardikk441",
    "location": "Ahmedabad, India",
    "timezone": "Asia/Kolkata",
    "currency": "INR",
    "core_skills": [
        "Node.js", "API Integration", "Backend Development",
        "Automation", "Data Collection", "eCommerce", "Web Development"
    ]
}

class FreelancerBidder:
    def __init__(self, oauth_token: Optional[str] = None):
        self.oauth_token = oauth_token or os.getenv("FREELANCER_API_TOKEN")
        self.user_id = HARDIK_PROFILE["user_id"]
        self.username = HARDIK_PROFILE["username"]

    def submit_bid(
        self,
        project_id: int,
        amount: float,
        period_days: int = 2,
        proposal_text: str = "",
        milestone_percentage: int = 100
    ) -> Dict[str, Any]:
        """
        Submits an official bid to a live project on Freelancer.com/Freelancer.in
        using Freelancer's public REST API.
        """
        if not self.oauth_token:
            return {
                "success": False,
                "mode": "MANUAL_1_CLICK",
                "error": "FREELANCER_API_TOKEN not set in environment.",
                "instructions": (
                    "To enable 100% zero-touch autonomous auto-bidding on hardikk441:\n"
                    "1. Go to https://www.freelancer.com/developers\n"
                    "2. Create Personal Access Token\n"
                    "3. Set environment variable: FREELANCER_API_TOKEN=<your_token>"
                ),
                "bidder_id": self.user_id,
                "project_id": project_id,
                "direct_url": f"https://www.freelancer.com/projects/{project_id}"
            }

        url = "https://www.freelancer.com/api/projects/0.1/bids/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AlgoriseHarvester/2.0",
            "Freelancer-Developer-Auth": f"{self.user_id};{self.oauth_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "project_id": int(project_id),
            "bidder_id": self.user_id,
            "amount": float(amount),
            "period": int(period_days),
            "milestone_percentage": int(milestone_percentage),
            "description": proposal_text
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "mode": "HEADLESS_API",
                    "bid_id": res_data.get("result", {}).get("id"),
                    "project_id": project_id,
                    "response": res_data
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            return {
                "success": False,
                "status_code": e.code,
                "error": err_body
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

freelancer_bidder = FreelancerBidder()
