"""kultuurivara.ee — The Events Calendar REST API (Kuressaare kontserdid, laadad jm)."""
from __future__ import annotations

from ..common import Event, clean_text, get, today

NAME = "kultuurivara.ee"
API = "https://www.kultuurivara.ee/wp-json/tribe/events/v1/events"


def fetch() -> list[Event]:
    out: list[Event] = []
    page = 1
    while True:
        j = get(API, params={"per_page": 50, "page": page, "start_date": today().isoformat()}).json()
        for e in j.get("events", []):
            venue = e.get("venue") or {}
            if isinstance(venue, list):
                venue = venue[0] if venue else {}
            loc = ", ".join(x for x in [venue.get("venue"), venue.get("city")] if x)
            all_day = bool(e.get("all_day"))
            start = e["start_date"][:10] if all_day else e["start_date"][:16].replace(" ", "T")
            end = e.get("end_date")
            end = (end[:10] if all_day else end[:16].replace(" ", "T")) if end else None
            if end == start or (end and all_day and end[:10] == start[:10]):
                end = None
            img = e.get("image") or {}
            out.append(Event(
                title=clean_text(e.get("title")),
                start=start,
                end=end,
                all_day=all_day,
                url=e.get("url", ""),
                source=NAME,
                location=clean_text(loc),
                price=clean_text(e.get("cost")),
                image=img.get("url", "") if isinstance(img, dict) else "",
                description=clean_text(e.get("description"), 400),
                raw_categories=[c["name"] for c in e.get("categories", [])] + [t["name"] for t in e.get("tags", [])],
            ))
        if page >= int(j.get("total_pages") or 1):
            break
        page += 1
    return out
