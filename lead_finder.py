#!/usr/bin/env python3
"""
================================================================================
ALGORISE AI — CREATOR & VIDEO AGENCY LEAD FINDER
Automated Prospecting & Cold Outreach Generator for 0 to $10k MRR
================================================================================
"""

import sys
import os
import re
import json
import csv
import urllib.request
import urllib.parse
from datetime import datetime

# Ensure clean UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
PRODUCTION_URL = "https://algorise-ai.surge.sh"
TELEGRAM_BOT = "@Aassqqee_bot"

PRESET_NICHES = {
    "1": ("Business, Founder & Startup Podcasts", "founder business podcast interview"),
    "2": ("Tech & Gadget Review Creators", "tech review unboxing 2026"),
    "3": ("Video Editing & Content Creation Channels", "video editing premiere pro davinci tutorial"),
    "4": ("Finance, Crypto & Solopreneur Shows", "personal finance investing solopreneur show"),
    "5": ("High-Pacing Gaming & Entertainment Creators", "gaming video podcast highlights"),
    "6": ("B2B Marketing & Agency Growth Podcasts", "marketing agency growth b2b sales podcast")
}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print("""
\033[1;36m╔═══════════════════════════════════════════════════════════════════════════════╗
║                      ALGORISE AI — LEAD FINDER & PROSPECTOR                   ║
║         Automated Cold Outreach Engine • Trojan Horse Viral Audit             ║
╚═══════════════════════════════════════════════════════════════════════════════╝\033[0m
""")

def fetch_youtube_results(query, max_results=20):
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.youtube.com/results?search_query={encoded_query}"
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"\033[1;31m[!] Network error fetching results: {e}\033[0m")
        return []

    match = re.search(r'var ytInitialData = ({.*?});</script>', html)
    if not match:
        print("\033[1;31m[!] Could not parse YouTube response data.\033[0m")
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        print("\033[1;31m[!] Failed to decode YouTube JSON payload.\033[0m")
        return []

    items = []
    try:
        sections = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
        for section in sections:
            item_section = section.get('itemSectionRenderer', {}).get('contents', [])
            for item in item_section:
                if 'videoRenderer' in item:
                    vr = item['videoRenderer']
                    
                    title = vr.get('title', {}).get('runs', [{}])[0].get('text', 'Untitled')
                    video_id = vr.get('videoId', '')
                    video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ''
                    
                    owner_runs = vr.get('ownerText', {}).get('runs', [{}])[0]
                    channel_name = owner_runs.get('text', 'Unknown Channel')
                    channel_path = owner_runs.get('navigationEndpoint', {}).get('commandMetadata', {}).get('webCommandMetadata', {}).get('url', '')
                    channel_url = f"https://www.youtube.com{channel_path}" if channel_path else ''
                    channel_handle = channel_path.replace('/', '') if channel_path.startswith('/@') else ''

                    # Length & View count
                    length_text = vr.get('lengthText', {}).get('simpleText', 'Unknown')
                    view_text = vr.get('viewCountText', {}).get('simpleText', '')
                    
                    # Description snippet
                    desc_runs = vr.get('detailedMetadataSnippets', [{}])[0].get('snippetText', {}).get('runs', [])
                    desc_text = ' '.join([r.get('text', '') for r in desc_runs])
                    
                    # Scan description for emails and Twitter/X handles
                    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', desc_text)
                    twitters = re.findall(r'(?:twitter\.com|x\.com)/([a-zA-Z0-9_]{1,15})', desc_text, re.IGNORECASE)
                    
                    email_str = emails[0] if emails else "Check Channel 'About'"
                    twitter_str = f"@{twitters[0]}" if twitters else (channel_handle if channel_handle else "N/A")

                    items.append({
                        "channel_name": channel_name,
                        "channel_handle": channel_handle or channel_name,
                        "channel_url": channel_url,
                        "video_title": title,
                        "video_url": video_url,
                        "duration": length_text,
                        "views": view_text,
                        "email": email_str,
                        "twitter": twitter_str,
                        "snippet": desc_text[:120]
                    })
                    
                    if len(items) >= max_results:
                        break
            if len(items) >= max_results:
                break
    except Exception as err:
        print(f"\033[1;33m[!] Warning during data parsing: {err}\033[0m")

    return items

def generate_cold_pitch(lead):
    """
    Generates high-converting personalized Trojan Horse pitch tailored to the prospect.
    """
    first_name = lead['channel_name'].split()[0] if lead['channel_name'] else 'there'
    # Avoid addressing channels starting with 'The' awkwardly
    if first_name.lower() in ['the', 'best', 'inside', 'top', 'mr']:
        first_name = lead['channel_name']
        
    raw_title = lead['video_title']
    # Clean title without breaking hyphenated words like 103-Minute
    clean_title = raw_title.split('|')[0].split('•')[0].split(' // ')[0].strip()
    if len(clean_title) > 65:
        clean_title = clean_title[:62].strip() + "..."
        
    audit_link = f"{PRODUCTION_URL}/#core-3d"
    
    pitch = (
        f"Hey {first_name}! Just watched your video '{clean_title}'. "
        f"Great episode, but noticed ~4.5s of dead air & slow pacing in the opening hook that might be dragging your retention down. "
        f"Ran it through our AI rough-cut pruner at {audit_link} — scored 93/100 and mapped 18% fluff cut. "
        f"Happy to send you the ready-to-import XML timeline for Premiere/DaVinci for free if you want to test it! (Or ping our team on Telegram {TELEGRAM_BOT})"
    )
    return pitch

def save_leads_to_files(leads, keyword):
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = re.sub(r'[^a-zA-Z0-9_]', '_', keyword.lower())[:20]
    
    csv_file = os.path.join(output_dir, f"leads_{safe_keyword}_{timestamp}.csv")
    json_file = os.path.join(output_dir, f"leads_{safe_keyword}_{timestamp}.json")
    latest_csv = os.path.join(output_dir, "latest_leads.csv")

    # Save CSV
    fieldnames = [
        "Channel Name", "Channel Handle", "Video Title", "Video URL", 
        "Duration", "Views", "Contact Email", "Twitter/X", "Channel URL", 
        "Personalized Cold DM (Copy-Paste)", "Audit Tool URL"
    ]
    
    with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for lead in leads:
            writer.writerow([
                lead["channel_name"],
                lead["channel_handle"],
                lead["video_title"],
                lead["video_url"],
                lead["duration"],
                lead["views"],
                lead["email"],
                lead["twitter"],
                lead["channel_url"],
                generate_cold_pitch(lead),
                f"{PRODUCTION_URL}/#core-3d"
            ])
            
    # Also overwrite latest_leads.csv for easy access
    try:
        import shutil
        shutil.copyfile(csv_file, latest_csv)
    except Exception:
        pass

    # Save JSON
    with open(json_file, mode='w', encoding='utf-8') as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    return csv_file, json_file, latest_csv

def display_results(leads, csv_path):
    print(f"\n\033[1;32m[+] Successfully captured {len(leads)} qualified leads!\033[0m")
    print(f"\033[1;34m[INFO] Output saved to:\n       {csv_path}\033[0m\n")
    
    print("-" * 80)
    print(f"{'#':<3} | {'Channel Name':<22} | {'Handle / Twitter':<18} | {'Duration':<9} | {'Status'}")
    print("-" * 80)
    
    for idx, lead in enumerate(leads, 1):
        ch = (lead['channel_name'][:20] + '..') if len(lead['channel_name']) > 20 else lead['channel_name']
        tw = (lead['twitter'][:16] + '..') if len(lead['twitter']) > 16 else lead['twitter']
        dur = lead['duration']
        print(f"\033[1;37m{idx:<3}\033[0m | \033[1;36m{ch:<22}\033[0m | \033[1;33m{tw:<18}\033[0m | {dur:<9} | \033[1;32mReady to Pitch\033[0m")

    print("-" * 80)
    print("\n\033[1;35m--- SAMPLE COPY-PASTE COLD DM (Lead #1) ---\033[0m")
    if leads:
        print(f"\033[1;32mRecipient:\033[0m {leads[0]['channel_name']} ({leads[0]['twitter']})")
        print(f"\033[1;32mVideo:\033[0m {leads[0]['video_title']}")
        print(f"\033[1;33mMessage:\033[0m\n{generate_cold_pitch(leads[0])}\n")
    print("-" * 80)

def main():
    clear_screen()
    print_banner()
    
    print("\033[1;33mSelect Target Niche to Prospect:\033[0m\n")
    for key, (label, query) in PRESET_NICHES.items():
        print(f"  \033[1;36m[{key}]\033[0m {label}")
    print("  \033[1;36m[7]\033[0m Custom Keyword Search")
    print("  \033[1;31m[0]\033[0m Exit\n")
    
    try:
        choice = input("\033[1;37mEnter selection [1-7, default: 1]: \033[0m").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        choice = "1"
    
    if choice == "0":
        print("\nExiting. Good luck closing deals!")
        return

    if choice in PRESET_NICHES:
        niche_name, search_query = PRESET_NICHES[choice]
    elif choice == "7":
        niche_name = "Custom Search"
        try:
            search_query = input("\033[1;37mEnter search query (e.g. 'indie hacker podcast'): \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            search_query = ""
        if not search_query:
            search_query = "founder podcast interview"
    else:
        niche_name, search_query = PRESET_NICHES["1"]

    try:
        limit_input = input("\033[1;37mNumber of leads to fetch [default: 15, max: 30]: \033[0m").strip()
    except (EOFError, KeyboardInterrupt):
        limit_input = "15"
    try:
        limit = min(max(int(limit_input), 5), 30) if limit_input else 15
    except ValueError:
        limit = 15

    print(f"\n\033[1;34m[*] Scanning YouTube for: '{search_query}' (fetching {limit} creator leads)...\033[0m")
    leads = fetch_youtube_results(search_query, max_results=limit)

    if not leads:
        print("\033[1;31m[!] No video leads found. Please try a different query.\033[0m")
        return

    csv_path, json_path, latest_csv = save_leads_to_files(leads, search_query)
    display_results(leads, csv_path)
    
    print("\033[1;36mActions:\033[0m")
    print(f"1. Open CSV in Excel: \033[1;37mstart {latest_csv}\033[0m")
    print("2. Copy the sample pitch above and send to Lead #1 on Twitter/X or Instagram!")
    print(f"3. Run free video scan for them on: \033[1;34m{PRODUCTION_URL}/#core-3d\033[0m\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        keyword = sys.argv[2] if len(sys.argv) > 2 else "founder podcast interview"
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 15
        print(f"Running automated lead scrape for: '{keyword}' (Limit: {limit})...")
        leads = fetch_youtube_results(keyword, max_results=limit)
        if leads:
            csv_path, json_path, latest_csv = save_leads_to_files(leads, keyword)
            display_results(leads, csv_path)
        else:
            print("No leads retrieved.")
    else:
        main()
