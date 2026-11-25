"""Saaremaa Teataja — Saaremaa vallavalitsuse kuine infoleht (PDF).

Vallalehe lehelt leitakse viimane number, PDF-ist otsitakse sündmuste lehekülg
(rubriik "Kultuuri- ja spordisündmused") ja loetakse sealt punktiloend:

    KIHELKONNA                      ← piirkond
    KIHELKONNA RAHVAMAJA            ← toimumiskoht
     • 29. novembril kell 17 heategevuslik advendikontsert
     • 9. detsembril kell 12 eakate jõululõuna, info 527 0436

Lehe küljendus võib numbriti muutuda — kui lugemine ebaõnnestub, jääb see allikas
lihtsalt tühjaks ja teised allikad töötavad edasi.
"""
from __future__ import annotations

import io
import logging
import re
from datetime import date

from bs4 import BeautifulSoup

from ..common import Event, clean_text, get, today

NAME = "Saaremaa Teataja"
LIST_URL = "https://www.saaremaavald.ee/vallaleht"
BASE = "https://www.saaremaavald.ee"

logging.getLogger("pypdf").setLevel(logging.ERROR)

MONTH_STEMS = {"jaanuar": 1, "veebruar": 2, "märts": 3, "aprill": 4, "mai": 5, "juuni": 6, "juuli": 7,
               "august": 8, "septemb": 9, "oktoob": 10, "novemb": 11, "detsemb": 12}
ITEM_RE = re.compile(
    r"^(\d{1,2})\.\s*(" + "|".join(MONTH_STEMS) + r")\w*"
    r"(?:\s*(?:kell|kl)\s*(\d{1,2})(?:[.:](\d{2}))?(?:\s*(–|-|ja)\s*(\d{1,2})(?:[.:](\d{2}))?)?)?"
    r"\s*(.*)$",
    re.I,
)
# Kohanimi tekstis ("… Metsküla seltsimajas") → toimumiskoht
PLACE_IN_TEXT = re.compile(
    r"([A-ZÕÄÖÜ][\wõäöüšž-]+\s+(?:seltsimaja|rahvamaja|kultuurimaja|kultuurikeskus|kirik|koolimaja|mõis|"
    r"raamatukogu|spordihoone|spordikeskus)(?:s|es|us|as)?)\b"
)
INESSIVE = [("kultuurikeskuses", "kultuurikeskus"), ("spordikeskuses", "spordikeskus"), ("kirikus", "kirik"),
            ("seltsimajas", "seltsimaja"), ("rahvamajas", "rahvamaja"), ("kultuurimajas", "kultuurimaja"),
            ("koolimajas", "koolimaja"), ("mõisas", "mõis"), ("raamatukogus", "raamatukogu"),
            ("spordihoones", "spordihoone")]


def _latest_issue() -> tuple[str, date]:
    soup = BeautifulSoup(get(LIST_URL).text, "lxml")
    best = None
    for a in soup.select("a[href$='.pdf']"):
        m = re.search(r"Saaremaa Teataja\s+(\d{4})[._](\d{2})(?:[._](\d{2}))?", a.get_text(" "))
        if not m:
            continue
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1))
        if best is None or d > best[1]:
            best = (a["href"], d)
    if not best:
        raise RuntimeError("Vallalehe lehelt ei leitud ühtegi Saaremaa Teataja PDF-i")
    href = best[0] if best[0].startswith("http") else BASE + best[0]
    return href, best[1]


def _events_text(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    for page in reader.pages:
        t = page.extract_text() or ""
        if "SÜNDMUSED" in t and t.count("•") >= 5:
            return t.split("KULTUURI- JA SPORDISÜNDMUSED")[0]
    return ""


def _nice_place(s: str) -> str:
    """'KARJA RAHVAMAJA' → 'Karja rahvamaja'; 'KURESSAARE TEATER' → 'Kuressaare Teater'."""
    if not s.isupper():
        return s
    words = s.lower().split()
    out = [words[0].capitalize()] + words[1:]
    return " ".join("Teater" if w == "teater" else w for w in out)


def _parse(text: str, issue: date) -> list[dict]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    items, region, venue, cur = [], None, None, None

    def flush():
        if cur:
            items.append(cur)

    for i, l in enumerate(lines[2:], start=2):           # 2 esimest rida on lehe päis
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if l.startswith("•"):
            flush()
            cur = {"region": region, "venue": venue, "text": l[1:].strip()}
            continue
        # tavakirjas piirkonnanimi ("Kihelkonna"), millele järgneb SUURTÄHTEDEGA koht
        if l.istitle() and l.isalpha() and len(l.split()) == 1 and nxt.isupper() and not nxt.startswith("•"):
            flush(); cur = None; region, venue = l.capitalize(), None
            continue
        if l.isupper() and l.replace(" ", "").replace("-", "").isalpha() and len(l) > 2:
            flush(); cur = None
            if len(l.split()) == 1 and l not in ("PÄEVAKESKUS", "RAHVAÜLIKOOL"):
                region, venue = l.capitalize(), None
            else:
                venue = l
            continue
        if cur:   # jätkurida; poolitatud sõnad kokku
            t = cur["text"]
            if t.endswith("-") and l[:1].islower():
                cur["text"] = t[:-1] + l
            elif t.endswith("-"):
                cur["text"] = t + l
            else:
                cur["text"] = t + " " + l
    flush()

    out = []
    for it in items:
        m = ITEM_RE.match(it["text"])
        if not m:
            continue
        day, mon, h1, m1, sep, h2, m2, rest = m.groups()
        month = MONTH_STEMS[next(s for s in MONTH_STEMS if mon.lower().startswith(s))]
        # aasta: lehe ilmumise aasta; kui kuu on lehe kuust palju varem (nt jaanuar detsembri lehes) → järgmine aasta
        year = issue.year + (1 if month < issue.month - 2 else 0)
        try:
            d = date(year, month, int(day))
        except ValueError:
            continue
        times = []
        if h1:
            times.append(f"{int(h1):02d}:{m1 or '00'}")
            if sep == "ja" and h2:
                times.append(f"{int(h2):02d}:{m2 or '00'}")
        end_time = f"{int(h2):02d}:{m2 or '00'}" if sep in ("–", "-") and h2 else None
        out.append({"date": d, "times": times or [None], "end_time": end_time,
                    "region": it["region"], "venue": it["venue"], "text": rest.strip()})
    return out


def _split_title(text: str) -> tuple[str, str]:
    """Esimene lause on pealkiri, ülejäänu kirjeldus."""
    text = re.sub(r"\s+", " ", text).strip(" .")
    m = re.search(r"(?<![A-ZÕÄÖÜ])\.\s+|!\s+", text)
    title, desc = (text[:m.start()], text[m.end():]) if m else (text, "")
    # pealkiri lõpeb esimese koma juures (", info …", ", õhtujuht …", ", pilet …")
    if ", " in title and title.index(", ") >= 8:
        cut = title.index(", ")
        title, desc = title[:cut], (title[cut + 2:] + (". " + desc if desc else "")).strip()
    title = title.strip(" –-")
    # „Kaval Ants ja Vana Pagan“ Esietendus! → Kaval Ants ja Vana Pagan (esietendus)
    qm = re.fullmatch(r"[„\"“]([^“\"”]+)[“\"”]\s*(.*)", title)
    if qm:
        title = qm.group(1) + (f" ({qm.group(2).strip(' !').lower()})" if qm.group(2).strip(" !") else "")
    return (title[:1].upper() + title[1:]), desc


def fetch() -> list[Event]:
    pdf_url, issue = _latest_issue()
    text = _events_text(get(pdf_url, timeout=180).content)
    if not text:
        raise RuntimeError(f"{pdf_url}: sündmuste lehekülge ei leitud (küljendus muutunud?)")
    t0 = today()
    events: list[Event] = []
    for it in _parse(text, issue):
        if it["date"] < t0:
            continue
        title, desc = _split_title(it["text"])
        full = it["text"]
        # toimumiskoht: pealkirjast/tekstist, muidu rubriigi koht, muidu piirkond
        place = ""
        pm = PLACE_IN_TEXT.search(full)
        if pm:
            place = pm.group(1)
            for a, b in INESSIVE:
                place = re.sub(a + r"$", b, place)
        elif it["venue"] and not it["venue"].endswith("KULTUURIVARA"):
            place = _nice_place(it["venue"])
            if (it["region"] or "").lower() == "kuressaare" and "kuressaare" not in place.lower():
                place = f"Kuressaare {place[:1].lower()}{place[1:]}"
        else:
            place = it["region"] or ""
        # rubriigi "Kuressaare Kultuurivara" puhul on koht lause lõpus: ", Kuressaare kultuurikeskus"
        if it["venue"] and it["venue"].endswith("KULTUURIVARA"):
            lm = re.search(r",\s*(Kuressaare [^,]+)$", full.strip(" ."))
            if lm:
                place = lm.group(1)
                for a, b in INESSIVE:
                    place = re.sub(a + r"$", b, place)
                title = re.sub(r",\s*Kuressaare [^,]+$", "", title)
        pr = re.search(r"(\d+(?:[.,]\d+)?\s*(?:/\s*\d+\s*)?€)", full)
        price = pr.group(1) if pr else ("Tasuta" if re.search(r"\btasuta\b", full, re.I) else "")
        raw = ["Teater"] if "teater" in (it["venue"] or "").lower() else []
        for tm in it["times"]:
            start = it["date"].isoformat() + (f"T{tm}" if tm else "")
            end = it["date"].isoformat() + f"T{it['end_time']}" if tm and it["end_time"] else None
            events.append(Event(
                title=title, start=start, end=None if end == start else end, all_day=tm is None,
                url=pdf_url, source=NAME, location=place, price=price,
                description=clean_text(desc, 400), raw_categories=raw,
            ))
    return events
