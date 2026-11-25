"""Käsitsi lisatud sündmused failist lisasundmused.txt (nt Facebookist nähtud üritused).

Rea kuju:  Kuupäev | Kell | Nimi | Koht | Link | Hind
Vigased read jäetakse vahele (koos hoiatusega), ülejäänud loetakse ikka sisse.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from ..common import Event

NAME = "Lisatud käsitsi"
FILE = Path(__file__).resolve().parents[2] / "lisasundmused.txt"

_DATE = r"(\d{1,2})\.(\d{1,2})\.(\d{4})|(\d{4})-(\d{2})-(\d{2})"
_TIME = re.compile(r"^(\d{1,2})[:.](\d{2})(?:\s*[-–]\s*(\d{1,2})[:.](\d{2}))?$")


def _parse_date(s: str) -> date:
    m = re.fullmatch(_DATE, s.strip())
    if not m:
        raise ValueError(f"kuupäev '{s}' — kasuta kuju 5.12.2026 või 2026-12-05")
    g = m.groups()
    try:
        return date(int(g[2]), int(g[1]), int(g[0])) if g[0] else date(int(g[3]), int(g[4]), int(g[5]))
    except ValueError:
        raise ValueError(f"kuupäeva '{s}' pole olemas (kontrolli päeva ja kuu numbrit)") from None


def fetch() -> list[Event]:
    if not FILE.exists():
        return []
    events: list[Event] = []
    for nr, line in enumerate(FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")] + [""] * 6
        d_s, t_s, title, place, link, price = parts[:6]
        try:
            if not title:
                raise ValueError("nimi puudub")
            # kuupäev või vahemik "5.12.2026-7.12.2026"
            rng = re.fullmatch(r"(.+?)\s*[-–]\s*(\d{1,2}\.\d{1,2}\.\d{4}|\d{4}-\d{2}-\d{2})", d_s)
            if rng and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d_s):
                d1, d2 = _parse_date(rng.group(1)), _parse_date(rng.group(2))
            else:
                d1, d2 = _parse_date(d_s), None
            start, end, all_day = d1.isoformat(), None, True
            if t_s:
                tm = _TIME.match(t_s)
                if not tm:
                    raise ValueError(f"kellaaeg '{t_s}' — kasuta kuju 18:00 või 18:00-20:00")
                h1, m1, h2, m2 = tm.groups()
                start, all_day = f"{d1.isoformat()}T{int(h1):02d}:{m1}", False
                if h2:
                    end = f"{(d2 or d1).isoformat()}T{int(h2):02d}:{m2}"
            if d2 and not end:
                end = d2.isoformat()
            if link and not re.match(r"https?://", link):
                link = "https://" + link
        except ValueError as ex:
            print(f"    ! lisasundmused.txt rida {nr}: {ex} — jäetakse vahele")
            continue
        events.append(Event(title=title, start=start, end=end, all_day=all_day, url=link,
                            source=NAME, location=place, price=price))
    return events
