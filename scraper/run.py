"""Kogub sündmused kõigist allikatest ja kirjutab app/events.json.

Käivitamine projekti kaustast:
    .venv\\Scripts\\python.exe -m scraper.run
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import traceback
import unicodedata
from datetime import timedelta
from pathlib import Path

from .categorize import CATEGORIES, categorize, is_kuressaare, is_theatre
from .common import Event, fix_caps, now, strip_emoji, today
from .sources import ical_sources, kultuurivara, lisasundmused, piletilevi, piletimaailm, saare_events, teataja

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "events.json"

SOURCES = [
    # nimi, avalik link, kogumisfunktsioon
    # Käsitsi lisatud esimesena: sinu enda kirjutatud pealkiri/kellaaeg on ühendamisel eelistatud
    ("Lisatud käsitsi", "", lisasundmused.fetch),
    ("saare.events","https://www.saare.events/", saare_events.fetch),
    ("saaresport.ee", "https://www.saaresport.ee/voistlused/kalender/", ical_sources.fetch_saaresport),
    ("saaremaaspordikool.ee", "https://saaremaaspordikool.ee/kalender/", ical_sources.fetch_spordikool),
    ("kultuurivara.ee", "https://www.kultuurivara.ee/", kultuurivara.fetch),
    ("piletilevi.ee", "https://www.piletilevi.ee/search?query=Kuressaare", piletilevi.fetch),
    ("piletimaailm.com", piletimaailm.SEARCH, piletimaailm.fetch),
    ("Saaremaa Teataja", teataja.LIST_URL, teataja.fetch),
]

# Allikate eelistus ühendamisel (väiksem = eelistatum põhiandmete jaoks)
PRIORITY = {name: i for i, (name, *_ ) in enumerate(SOURCES)}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s[:45]


# Üldsõnad, mida pealkirjade võrdlemisel ei arvestata
_TITLE_STOP = {
    "ja", "ning", "the", "and", "of", "etendus", "etenduse", "lavastus", "esietendus", "teater", "teatri",
    "kontsert", "kontserdi", "film", "kino", "uus", "kell", "live", "esitab", "esitavad", "presents",
}
# Kohasõnad, mis ei erista kohti üksteisest
# Ainult üldised piirkonnasõnad — kõik muu (ka "rahvamaja", "kirik") peab klappima.
_PLACE_STOP = {"saaremaa", "kuressaare", "saare", "maakond", "eesti", "linn", "vald", "saal", "sinine", "suur", "vaike"}


def _tokens(s: str, stop: set[str]) -> set[str]:
    return {w for w in _norm_full(s).split() if len(w) >= 3 and w not in stop}


def _norm_full(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _word_in(w: str, words: set[str]) -> bool:
    """Sõna leidub hulgas — võrreldakse algust (käänded: pagan / pagana)."""
    stem = w[:5]
    return any(x == w or (len(stem) >= 4 and x.startswith(stem)) for x in words)


def _same_event(a: Event, b: Event) -> bool:
    if a.start[:10] != b.start[:10]:
        return False
    # kellaaeg (kui mõlemal olemas) peab klappima ±15 min
    if len(a.start) > 10 and len(b.start) > 10:
        ma = int(a.start[11:13]) * 60 + int(a.start[14:16])
        mb = int(b.start[11:13]) * 60 + int(b.start[14:16])
        if abs(ma - mb) > 15:
            return False
    # Kui mõlemal on koht, peab lühema kohanime iga sõna leiduma pikemas.
    # Nii ei lähe kunagi kokku nt "Sandla rahvamaja" ja "Lümanda rahvamaja"
    # ega "Apollo Kino" ja "Thule Kino".
    pa, pb = _tokens(a.location, _PLACE_STOP), _tokens(b.location, _PLACE_STOP)
    if pa and pb:
        ps, pl = (pa, pb) if len(pa) <= len(pb) else (pb, pa)
        if not all(_word_in(w, pl) for w in ps):
            return False
    # lühema pealkirja kõik sisulised sõnad leiduvad pikemas
    ta, tb = _tokens(a.title, _TITLE_STOP), _tokens(b.title, _TITLE_STOP)
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if not short:
        return _norm_full(a.title) == _norm_full(b.title)
    if len(short) == 1 and len(next(iter(short))) < 6:
        return _norm_full(a.title) == _norm_full(b.title)   # üksik lühike sõna on liiga ebakindel
    if all(_word_in(w, long_) for w in short):
        return True
    # Sama koht (mõlemal märgitud) + sama päev (+ sama kellaaeg, kui mõlemal on):
    # piisab ühest ühisest pikast sisusõnast
    # ("Aastalõpupidu ansambliga Öö Sinuga" = "Aastalõpupidu Kärla rahvamajas").
    # Kohanimesid ("Laimjala", "rahvamaja") ühiseks sõnaks ei loeta.
    if pa and pb:
        place_words = _tokens(a.location + " " + b.location, set())
        common = [w for w in ta if len(w) >= 6 and not _word_in(w, place_words) and _word_in(w, tb)]
        return bool(common)
    return False


MERGE_LOG: list[tuple[str, str]] = []


def _merge(events: list[Event]) -> list[Event]:
    merged: list[Event] = []
    by_day: dict[str, list[Event]] = {}
    for e in sorted(events, key=lambda x: PRIORITY.get(x.source, 99)):
        src = {"name": e.source, "url": e.url}
        day = e.start[:10]
        base = next((x for x in by_day.get(day, []) if _same_event(x, e)), None)
        if base is None:
            e.sources = [src]
            e.id = hashlib.sha1(f"{_norm(e.title)}|{e.start}|{e.location}".encode()).hexdigest()[:12]
            by_day.setdefault(day, []).append(e)
            merged.append(e)
            continue
        if _norm_full(base.title) != _norm_full(e.title):
            MERGE_LOG.append((base.title, e.title))
        if src["name"] not in {s["name"] for s in base.sources}:
            base.sources.append(src)
        for f in ("location", "price", "image", "description", "end"):
            if not getattr(base, f) and getattr(e, f):
                setattr(base, f, getattr(e, f))
        if base.all_day and not e.all_day and e.start[:10] == base.start[:10]:
            base.start, base.all_day = e.start, False
        base.raw_categories += e.raw_categories
        base.theatre = base.theatre or e.theatre
    return merged


def main() -> int:
    t0 = today()
    horizon = (t0 + timedelta(days=365)).isoformat()
    all_events: list[Event] = []
    report = []
    for name, url, fn in SOURCES:
        print(f"→ {name} …", flush=True)
        try:
            evs = fn()
            for e in evs:
                e.title = fix_caps(strip_emoji(e.title))
                e.location = strip_emoji(e.location)
                e.description = strip_emoji(e.description)
                e.theatre = is_theatre(e.title, e.raw_categories, e.source)
            all_events += evs
            report.append({"name": name, "url": url, "ok": True, "count": len(evs)})
            print(f"  {len(evs)} sündmust")
        except Exception as ex:
            traceback.print_exc()
            report.append({"name": name, "url": url, "ok": False, "count": 0, "error": str(ex)[:200]})
            print(f"  VIGA: {ex}")

    merged = _merge(all_events)
    keep = []
    for e in merged:
        last_day = (e.end or e.start)[:10]
        if last_day < t0.isoformat() or e.start[:10] > horizon:
            continue
        e.categories = categorize(e.title, e.raw_categories, e.description, e.location)
        e.kuressaare = is_kuressaare(e.location)
        keep.append(e)
    keep.sort(key=lambda e: (e.start, e.title))

    # Kui kõik allikad ebaõnnestusid, ära kirjuta head faili tühjaks
    if not keep:
        print("Ühtegi sündmust ei leitud — events.json jääb muutmata.")
        return 1

    data = {
        "generated": now().isoformat(timespec="minutes"),
        "categories": [{"key": k, "label": l, "icon": i} for k, l, i in CATEGORIES],
        "sources": report,
        "events": [e.to_dict() for e in keep],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if MERGE_LOG:
        print(f"\nErineva pealkirjaga, kuid samaks loetud sündmused ({len(MERGE_LOG)}):")
        for a, b in sorted(set(MERGE_LOG)):
            print(f"  „{a}“  =  „{b}“")
    print(f"\nKokku {len(keep)} sündmust (enne ühendamist {len(all_events)}) → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
