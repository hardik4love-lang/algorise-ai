"""
Comprehensive Trial and Testing Suite for Algorise AI Solutions
Tests Facebook Agent NLP, Lead Detection, Auto-Reply, and API routes.
"""

import sys
import unittest
from datetime import datetime

# Set UTF-8 encoding for console output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1. Test Facebook Agent NLP & Heuristics
from engine.facebook_agent import FacebookAgentEngine

class TestFacebookAgent(unittest.TestCase):
    def setUp(self):
        self.agent = FacebookAgentEngine(api_version="v19.0")

    def test_gujarati_textile_hot_lead(self):
        comment = "તમારી પાસે 60 ગ્રામ જ્યોર્જેટ સાડીનો હોલસેલ ભાવ શું છે? 500 પીસનો ઓર્ડર કરવો છે. 9825012345 પર કેટલોગ મોકલો."
        score, status, intent = self.agent.classify_lead_intent(comment)
        print(f"\n[TRIAL 1: Gujarati Textile] Score: {score}, Status: {status}, Intent: {intent}")
        self.assertGreaterEqual(score, 75.0)
        self.assertEqual(status, "hot")

    def test_diamond_cvd_inquiry(self):
        comment = "CVD Round Brilliant 1.5 Carat D-VVS2 live rate please? Need urgent consignment for Mumbai buyer. WhatsApp on 9909245110"
        score, status, intent = self.agent.classify_lead_intent(comment)
        print(f"[TRIAL 2: Diamond CVD] Score: {score}, Status: {status}, Intent: {intent}")
        self.assertGreaterEqual(score, 75.0)
        self.assertEqual(status, "hot")

    def test_cold_spam_comment(self):
        comment = "Nice photo brother, congratulations!"
        score, status, intent = self.agent.classify_lead_intent(comment)
        print(f"[TRIAL 3: Spam/Cold] Score: {score}, Status: {status}, Intent: {intent}")
        self.assertLess(score, 50.0)
        self.assertEqual(status, "cold")

    def test_sector_autoreply_generation(self):
        reply_textile = self.agent.select_auto_reply("સાડી", sector="textile")
        self.assertIn("હોલસેલ કેટેલોગ", reply_textile)

        reply_diamond = self.agent.select_auto_reply("diamond", sector="diamond")
        self.assertIn("CVD & Lab-Grown Diamonds", reply_diamond)

        reply_realty = self.agent.select_auto_reply("flat", sector="realty")
        self.assertIn("સુરતના પ્રાઇમ લોકેશન", reply_realty)
        print("[TRIAL 4: Auto-Reply Templates] All sector templates verified successfully.")

    def test_agent_run_simulation(self):
        result = self.agent.process_client_agent_run(
            client_id="client_srt_test_001",
            client_name="Test Enterprise (Hardik)",
            business_name="Test Enterprise",
            page_id="104829104001",
            access_token="simulated_token",
            sector="textile",
            force_simulation=True
        )
        print(f"[TRIAL 5: Full Agent Run Simulation] Scanned: {result['comments_scanned']}, Replies: {result['replies_sent']}, Leads Detected: {result['leads_detected']}")
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["comments_scanned"], 0)
        self.assertGreater(result["leads_detected"], 0)

if __name__ == "__main__":
    unittest.main()
