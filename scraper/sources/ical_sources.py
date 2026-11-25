"""iCal-voogudega allikad (All-in-One Event Calendar WordPressi pistikprogramm).

- saaresport.ee — Saaremaa Spordiliidu võistluste kalender
- saaremaaspordikool.ee — Saaremaa Spordikooli kalender
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

import icalendar
import recurring_ical_events

from ..common import Event, TZ, clean_text, fmt_dt, get, today

AI1EC = "?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events&no_html=true"

FEEDS = [
    # (nimi, url, vaikimisi kategooria, välistatavate pealkirjade muster)
    ("saaresport.ee", "https://www.saaresport.ee/" + AI1EC, "Sport", None),
    ("saaremaaspordikool.ee", "https://saaremaaspordikool.ee/" + AI1EC, "Sport",
     re.compile(r"suletud|lahtiolek|treeningud ei toimu|puhkus", re.I)),
]

HORIZON_DAYS = 365


def _fetch_feed(name, url, default_cat, exclude) -> list[Event]:
    cal = icalendar.Calendar.from_ical(get(url, timeout=120).content)
    start = today()
    end = start + timedelta(days=HORIZON_DAYS)
    out: list[Event] = []
    for comp in recurring_ical_events.of(cal, skip_bad_series=True).between(start, end):
        title = clean_text(str(comp.get("SUMMARY", "")))
        if not title or (exclude and exclude.search(title)):
            continue
        dts = comp.get("DTSTART").dt
        dte = comp.get("DTEND").dt if comp.get("DTEND") else None
        all_day = not isinstance(dts, datetime)
        if all_day and dte and isinstance(dte, date):
            dte = dte - timedelta(days=1)   # iCal-is on kogu päeva lõpp välistav
        if isinstance(dts, datetime) and dts.tzinfo is None:
            dts = dts.replace(tzinfo=TZ)
        if isinstance(dte, datetime) and dte.tzinfo is None:
            dte = dte.replace(tzinfo=TZ)
        end_s = fmt_dt(dte, all_day) if dte else None
        start_s = fmt_dt(dts, all_day)
        if end_s == start_s or (end_s and end_s[:10] == start_s[:10] and all_day):
            end_s = None
        cats = []
        raw = comp.get("CATEGORIES")
        if raw:
            for c in (raw if isinstance(raw, list) else [raw]):
                cats += [str(x) for x in getattr(c, "cats", [c])]
        cats.append(default_cat)
        out.append(Event(
            title=title,
            start=start_s,
            end=end_s,
            all_day=all_day,
            url=str(comp.get("URL", "")) or url.split("?")[0],
            source=name,
            location=clean_text(str(comp.get("LOCATION", ""))),
            price="Tasuta" if str(comp.get("X-COST-TYPE", "")) == "free" and name == "saaresport.ee" else "",
            description=clean_text(str(comp.get("DESCRIPTION", "")), 400),
            raw_categories=cats,
        ))
    return out


def fetch_saaresport() -> list[Event]:
    return _fetch_feed(*FEEDS[0])


def fetch_spordikool() -> list[Event]:
    return _fetch_feed(*FEEDS[1])
