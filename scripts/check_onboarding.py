"""Verify the client onboarding SOP.

The onboarding SOP in INTEGRATION_PLAN.md section 3.3 lists five steps.
A new client needs the first two to exist and the last three to be
handled by the product rather than by editing code:

  1. Client record in clients
  2. Subscription record
  3. Meta access token through OAuth
  4. Sector selection driving the reply templates
  5. No merchant-specific data in the client code

Steps 1, 2, 4 and 5 are structural: the product either supports them or
it does not, and a regression in any of them is a build failure.

Step 3 depends on a Meta credential. A token cannot be committed, so its
absence is reported as a pending credential rather than as a failure.
Use --require-credentials to enforce it as well, which is the right
setting for a release or a production check.

Usage:
  python scripts/check_onboarding.py
  python scripts/check_onboarding.py --require-credentials
  python scripts/check_onboarding.py --json
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The reply code must not carry a merchant's contact details.
MERCHANT_LITERALS = (
    "63552 85433",
    "916355285433",
    "wa.me/916355285433",
)

# Directories that are served to a browser. A merchant number in any of
# them means the portal is single-tenant.
CLIENT_SURFACES = (
    "index.html",
    "dashboard.html",
    "admin.html",
    "creator_studio.html",
    "field_pitch.html",
    "realtor_sales_console.html",
    "cocopeat.html",
)

# Steps that need a credential rather than a code change.
CREDENTIAL_STEPS = {"step3_meta_token"}


def check_client_records():
    """Step 1: a client record exists and is active."""
    from engine.database import db_manager
    from engine.models_sqlalchemy import Client
    from sqlalchemy import select

    async def run():
        async with db_manager.session() as session:
            result = await session.execute(select(Client))
            clients = result.scalars().all()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "tier": c.tier,
                    "active": bool(c.is_active),
                    "has_page": bool(c.fb_page_id),
                    "has_token": bool(c.fb_access_token),
                    "has_phone": bool(c.phone),
                }
                for c in clients
            ]

    return asyncio.run(run())


def check_subscriptions():
    """Step 2: a subscription record exists for the client."""
    from engine.database import db_manager
    from engine.models_sqlalchemy import Subscription
    from sqlalchemy import select

    async def run():
        async with db_manager.session() as session:
            result = await session.execute(select(Subscription))
            subs = result.scalars().all()
            return [
                {
                    "client_id": s.client_id,
                    "plan_tier": s.plan_tier,
                    "status": s.status,
                }
                for s in subs
            ]

    return asyncio.run(run())


def check_meta_token(clients):
    """Step 3: a Meta access token is provisioned."""
    with_token = [c for c in clients if c["has_token"]]
    return {
        "ok": bool(with_token),
        "credential": True,
        "detail": (
            f"{len(with_token)} of {len(clients)} clients have a Meta access token"
            if with_token
            else "no client has a Meta access token; the sweep cannot read comments"
        ),
        "clients": [c["id"] for c in with_token],
    }


def check_sector(clients):
    """Step 4: a sector is selected and drives the reply templates."""
    from engine.facebook_agent import AUTO_REPLY_TEMPLATES

    configured = []
    for client in clients:
        from engine.database import db_manager
        from engine.models_sqlalchemy import Client
        from sqlalchemy import select

        async def run(client_id=client["id"]):
            async with db_manager.session() as session:
                result = await session.execute(
                    select(Client).where(Client.id == client_id)
                )
                row = result.scalars().first()
                if row is None:
                    return None
                settings = row.settings if isinstance(row.settings, dict) else {}
                rules = settings.get("agent_rules")
                rules = rules if isinstance(rules, dict) else {}
                return rules.get("sector") or settings.get("sector")

        sector = asyncio.run(run())
        if sector:
            configured.append({"client_id": client["id"], "sector": sector})

    known = {c["sector"] for c in configured}
    unsupported = known - set(AUTO_REPLY_TEMPLATES)
    return {
        "ok": bool(configured) and not unsupported,
        "detail": (
            f"sectors configured: {sorted(known)}"
            if configured
            else "no client has a sector selected"
        ),
        "configured": configured,
        "unsupported": sorted(unsupported),
    }


def check_no_merchant_literals():
    """Step 5: no merchant contact details in the code or the surfaces."""
    findings = []

    for path in sorted(ROOT.glob("engine/*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for literal in MERCHANT_LITERALS:
            if literal in text:
                findings.append(f"{path.relative_to(ROOT)}: {literal}")

    for name in CLIENT_SURFACES:
        path = ROOT / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for literal in MERCHANT_LITERALS:
            if literal in text:
                findings.append(f"{name}: {literal}")

    return {
        "ok": not findings,
        "detail": (
            "no merchant contact details in the code or the client surfaces"
            if not findings
            else f"{len(findings)} hardcoded merchant reference(s) remain"
        ),
        "findings": findings,
    }


def collect_paths(routes, seen=None, depth=0):
    """Recursively collect every registered path.

    FastAPI 0.159 keeps an included router as a single entry instead of
    copying its routes into app.routes, so a flat scan undercounts on
    that release. The OpenAPI schema is the authoritative view and is
    used as the primary source here.
    """
    if seen is None:
        seen = set()
    if depth > 6:
        return seen

    for route in routes or []:
        path = getattr(route, "path", None)
        if path:
            seen.add(path)

        original = getattr(route, "original_router", None)
        if original is not None:
            collect_paths(getattr(original, "routes", None), seen, depth + 1)

        candidates = getattr(route, "effective_candidates", None)
        if callable(candidates):
            try:
                candidates = candidates()
            except Exception:
                candidates = None
        if candidates:
            for candidate in candidates:
                candidate_path = getattr(candidate, "path", None)
                if candidate_path:
                    seen.add(candidate_path)
                collect_paths(getattr(candidate, "routes", None), seen, depth + 1)

        inner = getattr(route, "router", None)
        if inner is not None and getattr(inner, "routes", None):
            collect_paths(inner.routes, seen, depth + 1)

        nested = getattr(route, "routes", None)
        if nested and not path:
            collect_paths(nested, seen, depth + 1)

    return seen


def check_routes():
    """The API exposes the onboarding endpoints."""
    from engine.main import app

    paths = collect_paths(app.routes)

    # The OpenAPI schema is what the service actually serves.
    try:
        paths |= set(app.openapi().get("paths", {}))
    except Exception:
        pass

    required = {
        "/api/v1/subscribe": "client creation from the booking form",
        "/api/v1/auth/client-login": "client PIN login",
        "/api/v1/auth/facebook": "Meta OAuth start",
        "/api/v1/auth/facebook/callback": "Meta OAuth callback",
        "/api/v1/auth/facebook/manual-token": "manual token entry",
    }
    missing = {
        path: why for path, why in required.items() if path not in paths
    }
    return {
        "ok": not missing,
        "detail": (
            f"all onboarding endpoints are registered ({len(paths)} paths served)"
            if not missing
            else f"{len(missing)} onboarding endpoint(s) missing"
        ),
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-credentials",
        action="store_true",
        help="also fail when a credential such as the Meta token is missing",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    results = {}

    clients = check_client_records()
    results["step1_client_record"] = {
        "ok": bool(clients),
        "detail": f"{len(clients)} client record(s)",
        "clients": clients,
    }

    subs = check_subscriptions()
    results["step2_subscription"] = {
        "ok": bool(subs),
        "detail": f"{len(subs)} subscription record(s)",
    }

    results["step3_meta_token"] = check_meta_token(clients)
    results["step4_sector"] = check_sector(clients)
    results["step5_no_merchant_literals"] = check_no_merchant_literals()
    results["onboarding_endpoints"] = check_routes()

    structural = [
        name for name, result in results.items()
        if not result["ok"] and name not in CREDENTIAL_STEPS
    ]
    pending = [
        name for name, result in results.items()
        if not result["ok"] and name in CREDENTIAL_STEPS
    ]

    failed = structural + (pending if args.require_credentials else [])

    if args.json:
        print(json.dumps(
            {
                "results": results,
                "structural_failures": structural,
                "pending_credentials": pending,
                "failed": failed,
            },
            indent=2,
        ))
        return 1 if failed else 0

    print("CLIENT ONBOARDING SOP")
    print("=" * 70)
    for name, result in results.items():
        if result["ok"]:
            status = "OK  "
        elif name in CREDENTIAL_STEPS:
            status = "CRED" if not args.require_credentials else "GAP "
        else:
            status = "GAP "
        print(f"  {status}  {name}")
        print(f"        {result['detail']}")
        for key in ("findings", "missing"):
            for item in result.get(key, []) or []:
                print(f"          - {item}")
    print()

    if structural:
        print(f"{len(structural)} structural gap(s): {', '.join(structural)}")
    if pending:
        message = (
            f"{len(pending)} step(s) need a credential: {', '.join(pending)}"
        )
        if args.require_credentials:
            print(f"{message} (enforced)")
        else:
            print(f"{message} (not enforced here)")
    if not structural and not pending:
        print("Every onboarding step is complete.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
