"""
Algorise Autonomous Browser Closer Bot (Playwright Chrome Driver)
Operates directly on the user's desktop browser to:
1. Auto-edit Freelancer profile (Tagline, Hourly Rate, Bio).
2. Auto-place bids on Freelancer.com/Freelancer.in upon Telegram approval without any API keys.
"""

import os
import sys
import time
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright

BROWSER_PROFILE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "browser_profile")

DEFAULT_HEADLINE = "Full-Stack Node.js Architect | AI Agents, API Integrations & Data Automation"
DEFAULT_HOURLY_RATE = "1800"
DEFAULT_BIO = """Full-stack software engineer and automation specialist with deep experience building production-grade Node.js/Python microservices, custom REST/GraphQL APIs, resilient web scrapers, and end-to-end automation workflows.

Core Engineering Expertise:
? Backend & Full-Stack: Node.js, Express, Python (FastAPI/Django), PostgreSQL, MySQL, Docker
? Automations & APIs: Custom Webhook microservices, Stripe, Twilio, CRM sync, Zapier/Make replacement
? Web Scraping & Data: Distributed crawlers, anti-detection Playwright/Scrapy, automated ETL pipelines
? AI & LLM Systems: Local Ollama, GraphRAG, AI customer chatbots, deterministic safety guardrails

Guarantees:
1. Turnkey, clean, documented code with zero technical debt
2. Rapid 24-48 hour MVP prototype delivery
3. Direct, transparent communication with daily milestone updates

Ready to execute your contract immediately. Let's build."""

class BrowserCloserBot:
    def __init__(self, user_data_dir: str = BROWSER_PROFILE_DIR):
        self.user_data_dir = user_data_dir
        os.makedirs(self.user_data_dir, exist_ok=True)

    def update_profile(
        self,
        username: str = "hardikk441",
        headline: str = DEFAULT_HEADLINE,
        rate: str = DEFAULT_HOURLY_RATE,
        bio: str = DEFAULT_BIO
    ) -> Dict[str, Any]:
        """Opens browser, navigates to profile, edits headline, rate, and bio, and saves."""
        with sync_playwright() as p:
            print(f"[BROWSER BOT] Launching Chrome on desktop...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                channel="chrome",
                args=["--start-maximized"]
            )
            page = context.new_page()
            url = f"https://www.freelancer.in/u/{username}"
            print(f"[BROWSER BOT] Navigating to {url}...")
            page.goto(url, timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(4)

            # Check if user needs to log in
            login_needed = False
            for sel in ['a:has-text("Log In")', 'button:has-text("Log In")', 'a[href*="/login"]']:
                if page.query_selector(sel):
                    login_needed = True
                    break

            if login_needed:
                print("==================================================================")
                print("[ACTION REQUIRED] Please log into Freelancer in the opened window!")
                print("==================================================================")
                # Wait until login completes (up to 120 seconds)
                for _ in range(60):
                    time.sleep(2)
                    if not page.query_selector('a:has-text("Log In"), button:has-text("Log In")'):
                        print("[BROWSER BOT] Logged in successfully!")
                        break
                page.goto(url, timeout=60000)
                time.sleep(3)

            # Click Edit Profile button
            edit_selectors = [
                'button:has-text("Edit Profile")',
                'a:has-text("Edit Profile")',
                '.edit-profile-btn',
                '[data-heading="edit-profile"]'
            ]
            clicked_edit = False
            for sel in edit_selectors:
                btn = page.query_selector(sel)
                if btn:
                    print(f"[BROWSER BOT] Clicking Edit Profile ({sel})...")
                    btn.click()
                    clicked_edit = True
                    time.sleep(2)
                    break

            if not clicked_edit:
                # Fallback: navigate directly to settings profile page
                print("[BROWSER BOT] Navigating to https://www.freelancer.in/users/settings/profile...")
                page.goto("https://www.freelancer.in/users/settings/profile", timeout=60000)
                time.sleep(3)

            # Fill Headline / Tagline
            tagline_selectors = [
                'input[name="tagline"]',
                'input#tagline',
                'input[placeholder*="Headline" i]',
                'input[placeholder*="Tagline" i]',
                'input[data-heading="tagline"]'
            ]
            for sel in tagline_selectors:
                inp = page.query_selector(sel)
                if inp:
                    inp.fill("")
                    inp.fill(headline)
                    print(f"[BROWSER BOT] Set Tagline via {sel}")
                    break

            # Fill Hourly Rate
            rate_selectors = [
                'input[name="hourly_rate"]',
                'input#hourly_rate',
                'input[placeholder*="Rate" i]',
                'input[data-heading="hourly_rate"]'
            ]
            for sel in rate_selectors:
                inp = page.query_selector(sel)
                if inp:
                    inp.fill("")
                    inp.fill(rate)
                    print(f"[BROWSER BOT] Set Hourly Rate via {sel}")
                    break

            # Fill Summary Bio
            bio_selectors = [
                'textarea[name="profile_description"]',
                'textarea#description',
                'textarea[placeholder*="Summary" i]',
                'textarea[data-heading="summary"]',
                'textarea'
            ]
            for sel in bio_selectors:
                inp = page.query_selector(sel)
                if inp:
                    inp.fill("")
                    inp.fill(bio)
                    print(f"[BROWSER BOT] Set Bio via {sel}")
                    break

            time.sleep(1)

            # Click Save
            save_selectors = [
                'button:has-text("Save")',
                'button[type="submit"]:has-text("Save")',
                'button.btn-primary:has-text("Save")',
                'input[type="submit"][value*="Save" i]'
            ]
            saved = False
            for sel in save_selectors:
                btn = page.query_selector(sel)
                if btn:
                    print(f"[BROWSER BOT] Clicking Save ({sel})...")
                    btn.click()
                    saved = True
                    time.sleep(4)
                    break

            # Take confirmation screenshot
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile_updated.png")
            page.screenshot(path=screenshot_path)
            print(f"[BROWSER BOT] Screenshot saved to {screenshot_path}")

            context.close()
            return {
                "success": saved,
                "screenshot": screenshot_path,
                "message": "Profile updated and saved successfully!" if saved else "Filled fields, please confirm save."
            }

    def place_bid(
        self,
        project_url: str,
        amount: float,
        period_days: int = 2,
        proposal_text: str = ""
    ) -> Dict[str, Any]:
        """Opens project URL in browser, fills in bid amount, period, and proposal, and clicks Place Bid."""
        with sync_playwright() as p:
            print(f"[BROWSER BOT] Opening project: {project_url}")
            context = p.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=False,
                channel="chrome",
                args=["--start-maximized"]
            )
            page = context.new_page()
            page.goto(project_url, timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)

            # Fill Bid Amount
            amt_selectors = [
                'input[name="bidAmount"]',
                'input#bidAmount',
                'input[id*="bid-amount"]',
                'input[placeholder*="Paid to you" i]'
            ]
            for sel in amt_selectors:
                inp = page.query_selector(sel)
                if inp:
                    inp.fill("")
                    inp.fill(str(int(amount)))
                    print(f"[BROWSER BOT] Set bid amount: {amount}")
                    break

            # Fill Period
            period_selectors = [
                'input[name="period"]',
                'input#period',
                'input[id*="period"]'
            ]
            for sel in period_selectors:
                inp = page.query_selector(sel)
                if inp:
                    inp.fill("")
                    inp.fill(str(period_days))
                    print(f"[BROWSER BOT] Set period: {period_days} days")
                    break

            # Fill Proposal Text
            desc_selectors = [
                'textarea[name="proposalDescription"]',
                'textarea#proposalDescription',
                'textarea[id*="description"]',
                'textarea[placeholder*="proposal" i]'
            ]
            for sel in desc_selectors:
                inp = page.query_selector(sel)
                if inp:
                    inp.fill("")
                    inp.fill(proposal_text)
                    print("[BROWSER BOT] Filled proposal pitch.")
                    break

            time.sleep(1)

            # Click Place Bid
            bid_btn_selectors = [
                'button:has-text("Place Bid")',
                'button[id*="place-bid"]',
                'button[type="submit"]:has-text("Place Bid")'
            ]
            placed = False
            for sel in bid_btn_selectors:
                btn = page.query_selector(sel)
                if btn:
                    print(f"[BROWSER BOT] Clicking Place Bid ({sel})...")
                    btn.click()
                    placed = True
                    time.sleep(5)
                    break

            context.close()
            return {
                "success": placed,
                "message": f"Bid placed successfully on {project_url}" if placed else "Bid form filled, manual review needed."
            }

browser_closer_bot = BrowserCloserBot()
