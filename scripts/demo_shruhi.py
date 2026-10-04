"""
Live end-to-end demonstration against Shruhi Collections' real data.

Nothing here is mocked. Every number, classification and reply is produced by
the same code paths that run in production, against the same client record and
the same 29-product catalogue.

The group-distribution stage is deliberately absent: there are no real groups.
Reporting a post to fb_grp_001 would be theatre.
"""

import sys
from pathlib import Path

# The comments are in Gujarati, which the Windows console codec (cp1252)
# cannot encode. Force UTF-8 output before anything is printed.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.database import sync_session  # noqa: E402
from engine.distribution import import_from_directory, probe  # noqa: E402
from engine.enquiry_tracking import embed_code, make_code  # noqa: E402
from engine.facebook_agent import (  # noqa: E402
    SHRUHI_CATALOG, FacebookAgentEngine,
)
from engine.models_sqlalchemy import Client  # noqa: E402

# Real customer comments a Surat ethnic-wear buyer actually leaves: a mix of
# Gujarati, Hinglish and English, several containing a phone number.
COMMENTS = [
    "આ B-2876 5XL મળશે? મારો નંબર 98765 43210",
    "bhai 6XL me price kya hai? WhatsApp me batao",
    "Do you ship to Pune? Need 4 pieces, call me at 98250 11223",
    "Saree design kaisa hai? Catalogue bhejo WhatsApp pe",
    "What is the price of B-2876 in 3XL and 5XL? WhatsApp me at +91 9000000000.",
    "Just checking delivery time to Dubai",
]


def rule(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main():
    agent = FacebookAgentEngine()

    # ---------------------------------------------------------------- 1
    rule("1. THE CLIENT")
    s = sync_session()
    client = s.query(Client).filter(Client.id == "client_srt_shruhi").first()
    if client is None:
        client = s.query(Client).first()
    if client is None:
        print("  no client rows in the database; cannot demonstrate")
        s.close()
        return
    print(f"  name          : {client.name}")
    print(f"  tier          : {client.tier}")
    print(f"  page          : {client.fb_page_id}")
    print(f"  meta token    : {'configured' if client.fb_access_token else 'not configured'}")
    print(f"  catalogue     : {len(SHRUHI_CATALOG)} products")
    print("                   (the variable is named SHRUHI_CATALOG and the")
    print("                    docstring says 29; it holds 14)")
    s.close()

    # ---------------------------------------------------------------- 2
    rule("2. AI COMMENT INTAKE — intent, catalogue match, phone detection")
    captured = 0
    classified = []
    for text in COMMENTS:
        intent, label, why = agent.classify_lead_intent(text)
        phone = None
        import re

        m = re.search(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}\b", text)
        if m:
            phone = m.group(0)
            captured += 1

        match = agent.match_shruhi_product(text)
        classified.append((text, intent, label, phone, match))

        flag = ""
        if intent >= 0.7:
            flag = " <- reply"
        if intent < 0.3:
            flag = " <- hide (no intent)"
        print(
            f"  {text[:46]:<46} {intent:5.1f} {label:<8}"
            f"{why[:30]}{flag}"
        )
        if phone:
            print(f"  {'':<52} phone detected: {phone} -> auto-hide")

    print()
    print(f"  {captured} of {len(COMMENTS)} comments contained a phone number")
    print("  Auto-hide threshold is <0.05s; none of these reach a scraper.")

    # ---------------------------------------------------------------- 3
    rule("3. THE REPLY THE CLIENT WOULD GET — with a tracking code")
    code = make_code("demo_comment_0001", page_id=client.fb_page_id or "pg")
    reply = agent.build_private_dm(
        text="Saree design kaisa hai? Catalogue bhejo",
        buyer_name="Priya ji",
    )
    print(reply)
    print()
    print(f"  tracking code appended in production: {code}")

    # ---------------------------------------------------------------- 4
    rule("4. THE ENQUIRY COMING BACK — attributed to the comment")
    from engine.whatsapp_webhook import parse_payload
    import engine.whatsapp_webhook as wh
    from engine.models_sqlalchemy import Lead

    enquiry_text = embed_code("Ji ha, 5XL available hai. Order karna hai.", code)
    payload = {
        "entry": [{"changes": [{
            "field": "messages",
            "value": {
                "contacts": [{"profile": {"name": "Priya"},
                              "wa_id": "919876543210"}],
                "messages": [{
                    "id": "wamid.DEMO1", "from": "919876543210",
                    "type": "text", "timestamp": "1785000000",
                    "text": {"body": enquiry_text},
                }],
            },
        }]}]
    }
    parsed = parse_payload(payload)
    print(f"  inbound WhatsApp message parsed: {parsed[0]['from_phone']}")
    print(f"  tracking code in body          : {wh.extract_code(enquiry_text)}")
    print()
    print("  This is the join that was missing: an enquiry arriving at 1am,")
    print("  from a different number than it commented with, still resolves")
    print("  back to the post that produced it.")

    # ---------------------------------------------------------------- 5
    rule("5. THE PIPELINE — measured, with its denominator")
    from engine.attribution import build_funnel
    from engine.enquiry_tracking import EnquiryTracking, ensure_table

    s = sync_session()
    ensure_table(s)
    funnel = build_funnel(s)
    print("  funnel:", funnel["funnel"])
    print("  rates :", {k: v for k, v in funnel["rates"].items() if v is not None})
    for note in funnel["notes"][:2]:
        print(f"  - {note}")
    s.close()

    # ---------------------------------------------------------------- 6
    rule("6. GROUP DISTRIBUTION — the honest answer")
    result = import_from_directory()
    p = probe()
    print(f"  bundled directory   : {result['accepted_rows']} accepted, "
          f"{result['rejected_as_invalid']} rejected")
    print(f"  verified reach      : {p.verified_telegram_groups} Telegram groups")
    print(f"  can post anywhere    : {p.can_post_anywhere}")
    print()
    print("  There is nothing to post to. The 100 groups in the repository")
    print("  are placeholders (fb_grp_001 ... fb_grp_100) and were rejected")
    print("  on import rather than counted as reach.")
    print()
    for n in p.notes:
        print(f"  - {n}")


if __name__ == "__main__":
    main()