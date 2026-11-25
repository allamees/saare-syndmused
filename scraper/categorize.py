"""Ühtne kategooriate süsteem. Iga allikas kasutab oma liigitust — siin viime
need ühisele kujule ja täiendame pealkirja/kirjelduse märksõnadega."""
from __future__ import annotations

import re

# võti, nimi, ikoon — selles järjekorras kuvatakse ka rakenduses
CATEGORIES = [
    ("film", "Film", ""),
    ("lava", "Muusika ja teater", ""),
    ("naitus", "Näitus ja kunst", ""),
    ("sport", "Sport ja liikumine", ""),
    ("pidu", "Pidu ja festival", ""),
    ("koolitus", "Koolitus ja loeng", ""),
    ("muu", "Muu", ""),
]

# Allikate enda kategooriad (väiketähtedes, osaline vaste)
# "lapsed" on ajutine märge: see muudetakse lõpus kas spordiks või peoks.
_SOURCE_MAP = [
    (r"muusika|music|kontsert|klassika|ooper|jazz|rock|pop|koor", "lava"),
    (r"teater|tants|etendus|ballett|stand-?up|theatre|dance|komöödia", "lava"),
    (r"^film$|kino|cinema|movie", "film"),
    (r"kunst|näitus|museum|muuseum|exhibition", "naitus"),
    (r"sport|liikumine|võistlus|jooks|matk", "sport"),
    (r"festival|pidu|suursündmus|jõulud|party", "pidu"),
    (r"laat|mess|toit|turg|food", "pidu"),
    (r"koolitus|konverents|loeng|seminar|training", "koolitus"),
    (r"laste|lapsed|pere|family|kids", "lapsed"),
]

# Märksõnad pealkirjas
_TITLE_MAP = [
    (r"kontsert|ansambel|orkest|\bkoor|muusika|\bdj\b|ooper|jazz|bänd|laulu?(õhtu|tund|ring)|plaadiesitlus|orel", "lava"),
    (r"teater|etendus|lavastus|tantsu?(etendus|lavastus)|ballett|stand-?up|komöödia|näitemäng|tsirkus", "lava"),
    (r"\bfilm|kino(õhtu|seanss)?\b", "film"),
    (r"näitus|galerii|ekspositsioon|kunsti", "naitus"),
    (r"võistlus|turniir|\bjooks|meistrivõistlus|karikas|\bmatk|orienteeru|ujumi|korvpall|jalgpall|"
     r"võrkpall|käsipall|\bmale\b|suusa|ratta|triatlon|maraton|\bliiga\b|kergejõustik|saalihoki|"
     r"tervisepäev|kõnd|jõusaal|treening|regatt|purjetami|tennis|sulgpall|lauatennis|judo|maadlus", "sport"),
    (r"festival|pidu\b|peod|jõulupidu|simman|tulede süütami|kuuse(tuled|süüt)|jaanituli|ooperipäevad|päevad\b|tähistami|aastapäev|"
     r"jõuluvana|jõulumaa|jõulud\b|advendi|kuusetuled|vastlap|mälumäng", "pidu"),
    (r"\blaat|laada|turg\b|jõuluturg|mess\b|degusteeri|toidu|kohvik|lõuna\b", "pidu"),
    (r"koolitus|loeng|seminar|konverents|töötuba|õpituba|meisterda|kursus|infopäev|kohtumine|arutelu|ettekanne|vestlusring|"
     r"raamatu|esitlus|raamatuklubi", "koolitus"),
    (r"\blastele|lasteetendus|lastelavastus|laste(pidu|päev|hommik|kontsert|teater|jõulu)|"
     r"\bpere(päev|pidu|le)?\b|nukuteater|nukuetendus|muinasjutt|noorte|kooliõpila", "lapsed"),
]

_SOURCE_RE = [(re.compile(p, re.I), k) for p, k in _SOURCE_MAP]
_TITLE_RE = [(re.compile(p, re.I), k) for p, k in _TITLE_MAP]


_THEATRE_SRC = re.compile(r"teater|theatre|etendus|lavastus|ballett|stand-?up|komöödia", re.I)
_NOT_THEATRE = re.compile(r"näitus|galerii|maal ja graafika|raamatu|esitlus", re.I)
_THEATRE_TITLE = re.compile(r"teater|etendus|lavastus|ballett|stand-?up|komöödia|näitemäng|nukuteater|draama", re.I)


def is_theatre(title: str, raw_categories: list[str], source: str = "") -> bool:
    """Kas tegu on teatrietendusega (rakendus näitab nende juures 🎭 ikooni)."""
    if source == "piletimaailm.com":
        return True
    if _NOT_THEATRE.search(title):
        return False
    return any(_THEATRE_SRC.search(r) for r in raw_categories) or bool(_THEATRE_TITLE.search(title))


# Kuressaare toimumiskohad — ka need, mille nimes linna nime pole
_KURESSAARE = re.compile(
    r"kuressaare|apollo kino|thule kino|thule koda|raegalerii|saare kek|ringtee|"
    r"saare maakonna keskraamatukogu|saaremaa kunstistuudio|arensburg|meri spa|john bull|"
    r"loode tammik|vallimaa|vanalinna kool|lossipark|raekoda|raekoja|omnom|sadama ait",
    re.I,
)


def is_kuressaare(location: str) -> bool:
    return bool(_KURESSAARE.search(location or ""))


_SPORT_PLACE = re.compile(r"spordikeskus|spordihoone|spordihall|staadion|võimla", re.I)


def categorize(title: str, raw_categories: list[str], description: str = "", location: str = "") -> list[str]:
    found: list[str] = []

    def add(k):
        if k not in found:
            found.append(k)

    for raw in raw_categories:
        for rx, key in _SOURCE_RE:
            if rx.search(raw.strip()):
                add(key)
    # Filmi pealkiri on teose nimi, mitte sündmuse kirjeldus ("Kohtumine miniaga"
    # ei ole koolitus) — kinoseansile märksõnade järgi kategooriaid ei lisa.
    if any(r.strip().lower() == "film" for r in raw_categories):
        return found
    for rx, key in _TITLE_RE:
        if rx.search(title):
            add(key)
    # Eraldi laste kategooriat ei ole: spordikeskuses toimuv on sport,
    # kõik muud laste sündmused lähevad (lisaks) peo ja festivali alla.
    if "lapsed" in found:
        found.remove("lapsed")
        if _SPORT_PLACE.search(location):
            add("sport")
        else:
            add("pidu")
    return found or ["muu"]
