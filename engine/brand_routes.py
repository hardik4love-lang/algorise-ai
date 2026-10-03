"""
Client brand configuration.

The dashboard hardcoded one merchant's phone numbers in 34 places: 23 wa.me
deep links and 10 pieces of display text. Onboarding a second merchant
therefore required editing HTML, which is a ceiling on revenue rather than a
bug.

This serves the brand block per client so the dashboard renders whatever
merchant is signed in. Fields absent from settings fall back to neutral
placeholders rather than to another merchant's data — leaking one client's
contact details to another would be worse than showing nothing.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from engine.security import verify_api_key

router = APIRouter(prefix="/api/v1/client", tags=["client-brand"])

PLACEHOLDER = "—"

DEFAULT_BRAND: dict[str, Any] = {
    "business_name": PLACEHOLDER,
    "whatsapp_number": PLACEHOLDER,
    "whatsapp_link": PLACEHOLDER,
    "second_number": PLACEHOLDER,
    "website": PLACEHOLDER,
    "city": PLACEHOLDER,
    "tagline": PLACEHOLDER,
}


class BrandUpdate(BaseModel):
    business_name: Optional[str] = None
    whatsapp_number: Optional[str] = None
    website: Optional[str] = None
    city: Optional[str] = None
    tagline: Optional[str] = None
    second_number: Optional[str] = None


def _digits(raw: Optional[str]) -> str:
    if not raw:
        return ""
    return "".join(c for c in str(raw) if c.isdigit())


def build_brand(client) -> dict[str, Any]:
    settings = client.settings or {}
    if isinstance(settings, str):
        import json

        try:
            settings = json.loads(settings)
        except ValueError:
            settings = {}

    brand = dict(DEFAULT_BRAND)
    brand.update({k: v for k, v in settings.items() if v})

    # The Client row is the source of truth where the brand block is silent.
    if client.name and brand["business_name"] == PLACEHOLDER:
        brand["business_name"] = client.name
    if client.city and brand["city"] == PLACEHOLDER:
        brand["city"] = client.city
    if client.phone and brand["whatsapp_number"] == PLACEHOLDER:
        brand["whatsapp_number"] = client.phone

    digits = _digits(brand["whatsapp_number"])
    brand["whatsapp_digits"] = digits
    # wa.me needs digits only, with no + or spaces.
    brand["whatsapp_link"] = (
        f"https://wa.me/{digits}" if len(digits) >= 10 else PLACEHOLDER
    )
    brand["whatsapp_display"] = (
        f"+{digits}" if digits else PLACEHOLDER
    )
    return brand


def _session():
    from engine.database import sync_session

    return sync_session()


def _load(client_id: str):
    from engine.models_sqlalchemy import Client

    session = _session()
    client = session.query(Client).filter(Client.id == client_id).first()
    return session, client


@router.get("/{client_id}/brand")
def get_brand(client_id: str, _: bool = Depends(verify_api_key)):
    """Brand block for a client. Never another merchant's data."""
    session, client = _load(client_id)
    try:
        if client is None:
            raise HTTPException(404, "client not found")
        return {"client_id": client_id, "brand": build_brand(client)}
    finally:
        session.close()


@router.put("/{client_id}/brand")
def update_brand(
    client_id: str, payload: BrandUpdate, _: bool = Depends(verify_api_key)
):
    """Write brand fields into the client's settings block."""
    import json

    session, client = _load(client_id)
    try:
        if client is None:
            raise HTTPException(404, "client not found")
        settings = client.settings or {}
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except ValueError:
                settings = {}
        updates = {
            k: v for k, v in payload.model_dump().items() if v
        }
        settings.update(updates)
        client.settings = json.dumps(settings)
        session.commit()
        return {"client_id": client_id, "brand": build_brand(client)}
    finally:
        session.close()