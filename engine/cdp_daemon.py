# Algorise Chrome CDP Autonomous Daemon
import os
import sys
import time
import subprocess
import urllib.request
import json
from playwright.sync_api import sync_playwright

CHROME_DEBUG_DIR = r"C:\Users\om\AppData\Local\Google\Chrome\User Data Debug"
os.makedirs(CHROME_DEBUG_DIR, exist_ok=True)

HEADLINE = "Full-Stack Node.js Architect | AI Agents, API Integrations & Data Automation"
HOURLY_RATE = "1800"
BIO = (
    "Full-stack software engineer and automation specialist with deep experience building production-grade "
    "Node.js/Python microservices, custom REST/GraphQL APIs, resilient web scrapers, and end-to-end automation workflows.\n\n"
    "Core Engineering Expertise:\n"
    "• Backend & Full-Stack: Node.js, Express, Python (FastAPI/Django), PostgreSQL, MySQL, Docker\n"
    "• Automations & APIs: Custom Webhook microservices, Stripe, Twilio, CRM sync, Zapier/Make replacement\n"
    "• Web Scraping & Data: Distributed crawlers, anti-detection Playwright/Scrapy, automated ETL pipelines\n"
    "• AI & LLM Systems: Local Ollama, GraphRAG, AI customer chatbots, deterministic safety guardrails\n\n"
    "Guarantees:\n"
    "1. Turnkey, clean, documented code with zero technical debt\n"
    "2. Rapid 24-48 hour MVP prototype delivery\n"
    "3. Direct, transparent communication with daily milestone updates\n\n"
    "Ready to execute your contract immediately. Let's build."
)

def start_chrome():
    try:
        with urllib.request.urlopen("http://localhost:9222/json/version", timeout=2) as resp:
            print("[CDP] Chrome already running on port 9222!")
            return None
    except Exception:
        pass

    print("[CDP] Launching Chrome on desktop with --remote-debugging-port=9222...")
    proc = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--remote-debugging-port=9222",
        f"--user-data-dir={CHROME_DEBUG_DIR}",
        "--start-maximized",
        "https://www.freelancer.in/login"
    ])
    time.sleep(4)
    return proc

def run():
    chrome_proc = start_chrome()

    with sync_playwright() as p:
        print("[CDP] Connecting Playwright over CDP to http://localhost:9222...")
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        
        print("[CDP] Connected to Chrome! Waiting for user login...")
        profile_updated = False

        while True:
            try:
                cur_url = page.url
                if not profile_updated:
                    if "login" not in cur_url and ("dashboard" in cur_url or "u/" in cur_url or "freelancer.in" in cur_url):
                        user_elem = page.query_selector('button[data-heading="user-menu"], a[href*="/users/logout"], a[href*="/u/"]')
                        if user_elem:
                            print("[CDP] LOGIN DETECTED! Updating profile now...")
                            page.goto("https://www.freelancer.in/u/hardikk441", timeout=60000)
                            time.sleep(4)
                            
                            edit_btn = page.query_selector('button:has-text("Edit Profile")')
                            if edit_btn:
                                edit_btn.click()
                                time.sleep(2)
                                
                                tag = page.query_selector('input[name="tagline"], input#tagline, input[data-heading="tagline"]')
                                if tag:
                                    tag.fill(HEADLINE)
                                    print("[CDP] Set Headline!")
                                    
                                rate = page.query_selector('input[name="hourly_rate"], input#hourly_rate, input[data-heading="hourly_rate"]')
                                if rate:
                                    rate.fill(HOURLY_RATE)
                                    print("[CDP] Set Hourly Rate!")
                                    
                                bio_elem = page.query_selector('textarea[name="profile_description"], textarea#description, textarea[data-heading="summary"]')
                                if bio_elem:
                                    bio_elem.fill(BIO)
                                    print("[CDP] Set Bio!")
                                    
                                time.sleep(1)
                                save = page.query_selector('button:has-text("Save")')
                                if save:
                                    save.click()
                                    print("[CDP] CLICKED SAVE! Profile updated successfully!")
                                    profile_updated = True
                                    time.sleep(4)
                                    
                                    ss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cdp_profile_success.png")
                                    page.screenshot(path=ss_path)
                                    print(f"[CDP] Screenshot saved to {ss_path}")

                time.sleep(3)
            except Exception as e:
                print(f"[CDP Loop Error] {e}")
                time.sleep(5)

if __name__ == "__main__":
    run()
