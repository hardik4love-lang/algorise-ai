"""
Freelancer One-Time Interactive Login & Profile Setup
Opens Chrome with the persistent automation profile (browser_profile/).
Waits for the user to log in once.
As soon as login is detected, automatically populates Headline, Rate, and Bio, and clicks Save!
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

BROWSER_PROFILE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "browser_profile")
os.makedirs(BROWSER_PROFILE_DIR, exist_ok=True)

HEADLINE = "Full-Stack Node.js Architect | AI Agents, API Integrations & Data Automation"
HOURLY_RATE = "1800"
BIO = """Full-stack software engineer and automation specialist with deep experience building production-grade Node.js/Python microservices, custom REST/GraphQL APIs, resilient web scrapers, and end-to-end automation workflows.

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

def main():
    print("==================================================================")
    print("      ALGORISE FREELANCER ONE-TIME DESKTOP LOGIN & SETUP          ")
    print("==================================================================")
    print(">> Launching Chrome window on your screen...")
    print(">> Please log into your Freelancer account (hardikk441).")
    print(">> The bot will automatically detect your login and complete your profile!")
    print("==================================================================")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=BROWSER_PROFILE_DIR,
            headless=False,
            channel="chrome",
            args=["--start-maximized"]
        )
        page = context.new_page()
        page.goto("https://www.freelancer.in/login", timeout=60000)

        # Wait indefinitely until logged in (check for logout button or profile avatar)
        print("[WAITING] Waiting for you to log in in the opened Chrome window...")
        logged_in = False
        for _ in range(180): # wait up to 6 minutes
            time.sleep(2)
            # Check if URL changed away from login and shows user elements
            cur_url = page.url
            if "login" not in cur_url and ("dashboard" in cur_url or "u/" in cur_url or "projects" in cur_url):
                logged_in = True
                break
            if page.query_selector('a[href*="/users/logout"], a[href*="/u/"], button[data-heading="user-menu"]'):
                logged_in = True
                break

        if not logged_in:
            print("[TIMEOUT] Login timeout reached. Please run the script again when ready.")
            context.close()
            return
        print("\n>> LOGIN DETECTED! Proceeding to update your profile automatically...")
        time.sleep(2)

        # Navigate to profile
        profile_url = "https://www.freelancer.in/u/hardikk441"
        page.goto(profile_url, timeout=60000)
        time.sleep(4)

        # Click Edit Profile
        print(">> Clicking 'Edit Profile' button...")
        edit_clicked = False
        for sel in ['button:has-text("Edit Profile")', 'a:has-text("Edit Profile")', '.edit-profile-btn']:
            btn = page.query_selector(sel)
            if btn:
                btn.click()
                edit_clicked = True
                print(f"   Clicked via {sel}")
                time.sleep(2)
                break

        # Fill inputs
        print(">> Auto-filling Headline, Hourly Rate, and Summary Bio...")
        # Headline
        for sel in ['input[name="tagline"]', 'input#tagline', 'input[data-heading="tagline"]']:
            inp = page.query_selector(sel)
            if inp:
                inp.fill("")
                inp.fill(HEADLINE)
                print("   Set Headline.")
                break

        # Rate
        for sel in ['input[name="hourly_rate"]', 'input#hourly_rate', 'input[data-heading="hourly_rate"]']:
            inp = page.query_selector(sel)
            if inp:
                inp.fill("")
                inp.fill(HOURLY_RATE)
                print("   Set Hourly Rate (1800).")
                break

        # Bio
        for sel in ['textarea[name="profile_description"]', 'textarea#description', 'textarea[data-heading="summary"]', 'textarea']:
            inp = page.query_selector(sel)
            if inp:
                inp.fill("")
                inp.fill(BIO)
                print("   Set Bio.")
                break

        time.sleep(1)

        # Save
        print(">> Saving changes...")
        for sel in ['button:has-text("Save")', 'button[type="submit"]:has-text("Save")']:
            btn = page.query_selector(sel)
            if btn:
                btn.click()
                print("   Clicked Save!")
                time.sleep(4)
                break

        screenshot_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile_saved_success.png")
        page.screenshot(path=screenshot_file)
        print(f"\n>> SUCCESS! Profile updated and saved. Screenshot saved to: {screenshot_file}")
        print(">> Your session is permanently saved in browser_profile/.")
        print(">> Automated browser bidding is now 100% active!")
        time.sleep(3)
        context.close()

if __name__ == "__main__":
    main()
