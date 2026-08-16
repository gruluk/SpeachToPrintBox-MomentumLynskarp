"""Default event config, privacy copy, interests, and booth flow graph."""

from __future__ import annotations

import copy
import re

DEFAULT_INTERESTS = [
    "Periodeavslutning",
    "Avsetninger og periodiseringer",
    "Interntransaksjoner",
    "Kostnader og varelager",
    "Budsjett og prognose",
    "Konsolidering",
    "Effektivisering av økonomifunksjonen",
    "Rapportering",
    "Lønnsomhet ved bruk av KI",
    "Praktisk bruk av KI",
]

DEFAULT_PRIVACY_TITLE = "Samtykke til bruk av dine opplysninger"

DEFAULT_PRIVACY_BULLETS = [
    "Vi lagrer navn, epost, telefonnummer og valgte interesseområder for å administrere din deltakelse på Lynskarp.",
    "Opplysningene brukes til å bekrefte registrering, lage navneskilt og eventuell oppfølging etter arrangementet.",
    "Du kan når som helst trekke samtykke tilbake ved å kontakte oss.",
    "All data slettes senest 90 dager etter at arrangementet er avsluttet.",
]

DEFAULT_PRIVACY_CHECKBOX = (
    "Jeg samtykker til at Sopra Steria lagrer og behandler opplysningene mine slik det er beskrevet over."
)


def default_flow() -> dict:
    """Railway-style default register + checkout flow with printer/attendees integrations."""
    return {
        "nodes": [
            {"id": "start", "type": "screen", "position": {"x": 80, "y": 200}, "data": {"screen": "start", "label": "Start"}},
            {"id": "privacy", "type": "screen", "position": {"x": 320, "y": 80}, "data": {"screen": "privacy", "label": "Personvern"}},
            {"id": "name", "type": "screen", "position": {"x": 560, "y": 80}, "data": {"screen": "name_input", "label": "Navn"}},
            {"id": "interests", "type": "screen", "position": {"x": 800, "y": 80}, "data": {"screen": "interest_select", "label": "Interesser"}},
            {"id": "done", "type": "screen", "position": {"x": 1040, "y": 80}, "data": {"screen": "done", "label": "Ferdig"}},
            {"id": "qr", "type": "screen", "position": {"x": 320, "y": 320}, "data": {"screen": "qr_scan", "label": "QR-skanning"}},
            {"id": "demo_matched", "type": "screen", "position": {"x": 560, "y": 320}, "data": {"screen": "demo_matched", "label": "Demo"}},
            {"id": "demo_done", "type": "screen", "position": {"x": 800, "y": 280}, "data": {"screen": "demo_done", "label": "Demo ferdig"}},
            {"id": "checkout_done", "type": "screen", "position": {"x": 800, "y": 400}, "data": {"screen": "checkout_done", "label": "Utsjekk"}},
            {"id": "printer", "type": "integration", "position": {"x": 1040, "y": 280}, "data": {"kind": "printer", "label": "Printer"}},
            {"id": "db", "type": "integration", "position": {"x": 80, "y": 400}, "data": {"kind": "attendees", "label": "Deltakere"}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "privacy", "data": {"action": "register"}},
            {"id": "e2", "source": "privacy", "target": "name", "data": {"action": "next"}},
            {"id": "e3", "source": "name", "target": "interests", "data": {"action": "next"}},
            {"id": "e4", "source": "interests", "target": "done", "data": {"action": "next"}},
            {"id": "e5", "source": "interests", "target": "printer", "data": {"action": "print_label"}},
            {"id": "e6", "source": "start", "target": "qr", "data": {"action": "checkout"}},
            {"id": "e7", "source": "qr", "target": "demo_matched", "data": {"action": "next"}},
            {"id": "e8", "source": "demo_matched", "target": "demo_done", "data": {"action": "wants_demo"}},
            {"id": "e9", "source": "demo_matched", "target": "checkout_done", "data": {"action": "no_demo"}},
            {"id": "e10", "source": "name", "target": "db", "data": {"action": "lookup"}},
        ],
    }


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[æ]", "ae", s)
    s = re.sub(r"[ø]", "o", s)
    s = re.sub(r"[å]", "a", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "event"


def default_event_fields(name: str = "Momentum Lynskarp", slug: str = "lynskarp") -> dict:
    return {
        "name": name,
        "slug": slug,
        "starts_at": "",
        "ends_at": "",
        "interests": list(DEFAULT_INTERESTS),
        "lookup_mode": "name",
        "allow_walkup_registration": False,
        "privacy_title": DEFAULT_PRIVACY_TITLE,
        "privacy_bullets": list(DEFAULT_PRIVACY_BULLETS),
        "privacy_checkbox_label": DEFAULT_PRIVACY_CHECKBOX,
        "flow": default_flow(),
        "max_interests": 3,
    }


def normalize_event(raw: dict) -> dict:
    """Ensure event dict has all fields with sensible defaults."""
    base = default_event_fields(raw.get("name") or "Event", raw.get("slug") or "event")
    out = {**base, **{k: v for k, v in raw.items() if v is not None}}
    out["id"] = raw.get("id", "")
    if not isinstance(out.get("interests"), list):
        out["interests"] = list(DEFAULT_INTERESTS)
    if not isinstance(out.get("privacy_bullets"), list):
        out["privacy_bullets"] = list(DEFAULT_PRIVACY_BULLETS)
    if not isinstance(out.get("flow"), dict) or "nodes" not in out["flow"]:
        out["flow"] = default_flow()
    else:
        out["flow"] = copy.deepcopy(out["flow"])
    out["lookup_mode"] = out.get("lookup_mode") or "name"
    if out["lookup_mode"] not in ("name", "phone", "both"):
        out["lookup_mode"] = "name"
    out["allow_walkup_registration"] = bool(out.get("allow_walkup_registration"))
    out["max_interests"] = int(out.get("max_interests") or 3)
    return out
