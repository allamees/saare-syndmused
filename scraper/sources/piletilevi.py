"""piletilevi.ee — avalik otsingu-API. Otsime Saare maakonna kohanimede järgi
ja jätame alles ainult sündmused, mille toimumiskoht asub Saare maakonnas."""
from __future__ import annotations

import re
from datetime import datetime

from ..common import Event, TZ, clean_text, get

NAME = "piletilevi.ee"
API = "https://www.piletilevi.ee/api/v1/search"
QUERIES = ["Kuressaare", "Saaremaa", "Muhu"]   # hoia päringuid vähe — Piletilevi piirab sagedust

SAARE_PLACES = re.compile(
    r"kuressaare|saaremaa|saare maakond|muhu|orissaare|ruhnu|kärla|leisi|valjala|"
    r"kihelkonna|mustjala|salme|torgu|laimjala|pöide|lümanda|nasva|sõrve|abruka|"
    r"angla|kaali|tornimäe|aste|liiva|koguva|panga|loona|kuressaare lossi",
    re.I,
)


def _to_local(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)


def fetch() -> list[Event]:
    out: dict[str, Event] = {}
    for q in QUERIES:
        page = 1
        while True:
            try:
                j = get(API, delay=4.0, params={"query": q, "language": "et", "page": page,
                                                "pageSize": 36, "sortBy": "score", "sortOrder": "DESC"}).json()
            except Exception as ex:
                # Piletilevi piirab päringuid — jätame alles, mis juba saime
                print(f"    ! piletilevi '{q}' lk {page}: {ex}")
                if not out:
                    raise   # kohe esimene päring keelati — ära jätka
                return list(out.values())
            ev = j.get("events") or {}
            for e in ev.get("items", []):
                venue = e.get("venue") or {}
                vtxt = " ".join(str(venue.get(k) or "") for k in ("name", "nameOverride", "city"))
                if not SAARE_PLACES.search(vtxt) or e["id"] in out or not e.get("eventStartAt"):
                    continue
                st = _to_local(e["eventStartAt"])
                en = _to_local(e["eventEndAt"]) if e.get("eventEndAt") else None
                img = ""
                if e.get("imageData"):
                    img = f"https://www.piletilevi.ee/i/width=600/images/{e['imageData'][0]['imageId']}"
                loc = venue.get("nameOverride") or venue.get("name") or ""
                if venue.get("city") and venue["city"].lower() not in loc.lower():
                    loc += f", {venue['city']}"
                out[e["id"]] = Event(
                    title=clean_text(e["name"]),
                    start=st.strftime("%Y-%m-%dT%H:%M"),
                    end=en.strftime("%Y-%m-%dT%H:%M") if en and en.date() != st.date() else None,
                    url=f"https://www.piletilevi.ee/piletid/{e['id']}/{e.get('sluggedName', '')}",
                    source=NAME,
                    location=loc,
                    image=img,
                    description=clean_text(e.get("description"), 400),
                    raw_categories=[c["name"] for c in e.get("categories", [])],
                    price="Välja müüdud" if e.get("badge") == "SOLD_OUT" else "",
                )
            if page >= int(ev.get("totalPages") or 1):
                break
            page += 1
    return list(out.values())
