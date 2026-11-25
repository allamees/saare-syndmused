"""saare.events — Saaremaa valla ametlik sündmuste portaal.

Samu andmeid näitavad ka kadi.ee, minusaaremaa.ee ja visitsaaremaa.ee,
seega katab see allikas ka need.

Leht kasutab lõputut kerimist: ?page=N tagastab KÕIK sündmused lehekülgedeni 0..N,
seega piisab ühest päringust suure N-iga.
"""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from ..common import Event, ET_MONTHS, get, infer_year, today

BASE = "https://www.saare.events"
NAME = "saare.events"

# (rada, lisakategooria)
LISTS = [("/events?page=80", None), ("/movies?page=40", "Film")]

_DATE_RE = re.compile(
    r"(\d{1,2})\s+(" + "|".join(ET_MONTHS) + r")\s*(\d{4})?\s*(\d{1,2}:\d{2})?",
    re.I,
)


def _parse_dates(text: str):
    """Tagastab (start_date, start_time, end_date, end_time)."""
    text = re.sub(r"\s+", " ", text)
    parts = [m.groups() for m in _DATE_RE.finditer(text)]
    if not parts:
        return None
    toks = []
    for d, mon, yr, tm in parts:
        toks.append([int(d), ET_MONTHS[mon.lower()], int(yr) if yr else None, tm])
    # lõpu aasta (kui puudub) järeldame tänasest; alguse aasta lõpu järgi
    last = toks[-1]
    if last[2] is None:
        last[2] = infer_year(last[1], last[0])
    if len(toks) > 1:
        first = toks[0]
        if first[2] is None:
            first[2] = last[2]
            if (first[1], first[0]) > (last[1], last[0]):
                first[2] -= 1
    s = toks[0]
    e = toks[-1] if len(toks) > 1 else None
    try:
        sd = date(s[2], s[1], s[0])
        ed = date(e[2], e[1], e[0]) if e else None
    except ValueError:
        return None
    return sd, s[3], ed, (e[3] if e else None)


def fetch() -> list[Event]:
    events: list[Event] = []
    seen: set[str] = set()
    for path, extra_cat in LISTS:
        soup = BeautifulSoup(get(BASE + path, timeout=90).text, "lxml")
        for art in soup.select("article.announcement-preview"):
            node = art.get("about", "")
            if not node or node in seen:
                continue
            seen.add(node)
            title_el = art.select_one(".card-title")
            date_el = art.select_one(".date")
            if not title_el or not date_el:
                continue
            parsed = _parse_dates(date_el.get_text(" "))
            if not parsed:
                continue
            sd, st, ed, et = parsed
            # pikaajaline näitus, mis on juba alanud: näitame tänasest
            all_day = st is None
            start = sd.isoformat() + (f"T{int(st.split(':')[0]):02d}:{st.split(':')[1]}" if st else "")
            end = None
            if ed and ed != sd:
                end = ed.isoformat() + (f"T{int(et.split(':')[0]):02d}:{et.split(':')[1]}" if et else "")
            img = ""
            img_el = art.select_one(".card-img")
            if img_el and (m := re.search(r"url\(([^)]+)\)", img_el.get("style", ""))):
                img = m.group(1).strip("'\"")
            price_el = art.select_one(".price")
            host_el = art.select_one(".host-by")
            cats = [i.get("alt", "") for i in art.select(".categories img") if i.get("alt")]
            if extra_cat:
                cats.append(extra_cat)
            events.append(Event(
                title=title_el.get_text(" ", strip=True),
                start=start,
                end=end,
                all_day=all_day,
                url=BASE + node,
                source=NAME,
                location=host_el.get_text(" ", strip=True) if host_el else "",
                price=price_el.get_text(" ", strip=True) if price_el else "",
                image=img,
                raw_categories=cats,
            ))
    return events
