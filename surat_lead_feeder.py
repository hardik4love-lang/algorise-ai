"""
================================================================================
ALGORISE AI — CONTINUOUS SURAT LEAD FEEDER & SCRAPER PIPELINE
Automated Discovery of Active Meta Advertisers & High-Ticket Commercial Targets
Surat Industrial Clusters: Ring Road, Katargam, Varachha, Vesu, Sachin GIDC
================================================================================
"""
import sys
import os
import re
import json
import sqlite3
from datetime import datetime, timezone

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "aria_production.db")

from aria_service import init_production_db
from surat_business_scraper import get_curated_surat_seed_leads

def sync_seed_leads():
    """Seeds verified commercial accounts into SQLite production database."""
    init_production_db()
    seed_leads = get_curated_surat_seed_leads()
    inserted = 0
    with sqlite3.connect(DB_PATH) as conn:
        for lead in seed_leads:
            dist = 4.0 if "Ring Road" in lead["market"] or "Radharaman" in lead["market"] else (
                5.0 if "Millennium" in lead["market"] or "Sahara" in lead["market"] else (
                    6.0 if "Adajan" in lead["market"] else 11.0
                )
            )
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO leads (phone, name, sector, market, zone, distance_km, remote_fee, visiting_fee, status)
                    VALUES (?, ?, ?, ?, ?, ?, 250.0, ?, 'ACTIVE');
                """, (
                    lead["phone"], lead["name"], lead["sector"], lead["market"],
                    lead["zone"], dist, float(lead["visiting_charge"])
                ))
                inserted += 1
            except Exception as e:
                print(f"Error syncing {lead['name']}: {e}")
        conn.commit()
    return inserted

if __name__ == "__main__":
    print("=" * 80)
    print("  ALGORISE AI — CONTINUOUS SURAT LEAD FEEDER PIPELINE")
    print("=" * 80)
    synced = sync_seed_leads()
    print(f"✅ Synced {synced} High-Ticket Surat Commercial Accounts into SQLite DB!")
    print(f"📁 Database Path: {DB_PATH}")
    print("=" * 80)
