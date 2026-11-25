"""Ühised abifunktsioonid: HTTP päringud, sündmuse andmekuju, kuupäevad."""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

TZ = ZoneInfo("Europe/Tallinn")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 SaareSyndmusedBot/1.0"
)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "et,en;q=0.8"})


def get(url: str, *, delay: float = 0.5, **kw) -> requests.Response:
    """Viisakas GET: väike paus enne päringut, aegumine 30 s."""
    time.sleep(delay)
    r = _session.get(url, timeout=kw.pop("timeout", 30), **kw)
    r.raise_for_status()
    return r


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()


@dataclass
class Event:
    title: str
    start: str                    # "2026-11-25T18:30" või "2026-11-25" (kogu päev)
    url: str
    source: str
    end: str | None = None
    all_day: bool = False
    location: str = ""
    price: str = ""
    image: str = ""
    description: str = ""
    raw_categories: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    id: str = ""
    theatre: bool = False
    kuressaare: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("source")
        d.pop("raw_categories")
        return d


def clean_text(s: str | None, limit: int | None = None) -> str:
    """Eemaldab HTML-märgendid, dekodeerib olemid ja tihendab tühikud."""
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>|</p>|</div>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s).strip()
    s = re.sub(r"\n{2,}", "\n", s)
    if limit and len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0] + "…"
    return s


_EMOJI = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # emotikonid, pildimärgid, sümbolid
    "☀-➿"           # mitmesugused sümbolid, dingbat'id (✨ ☀ ✔ ❤)
    "⬀-⯿"           # nooled, tähed (⭐ ⬆)
    "⌀-⏿"           # tehnilised sümbolid (⌚ ⏰)
    "️‍⃣"      # emotikonide variatsiooni- ja liitmärgid
    "]+"
)


def strip_emoji(s: str) -> str:
    """Eemaldab emotikonid ja tihendab tühikud."""
    if not s:
        return s
    s = _EMOJI.sub(" ", s)
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r" *\n *", "\n", s).strip()


_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_ROMAN = re.compile(r"^[IVXLC]+$")
# lühendid, mis jäävad suurtähtedega
_ACRONYMS = {"KEK", "MTÜ", "EMV", "SAI", "DJ", "MV", "LT", "EV", "ERR", "EKRE", "TV", "USA", "EU", "EL",
             "FC", "JK", "SK", "PL", "KK", "VK", "OÜ", "SA"}
# Need lühendid kirjutatakse pealkirjas ALATI suurtähtedega (ka kui allikas kirjutas "fc" / "Sk")
_ALWAYS_UPPER = re.compile(r"\b(fc|jk|sk|pl|kk|vk|mtü|oü|mv|emv)\b", re.I)
# kohanimed, mis peavad jääma suure algustähega
_PLACES = {
    "saare", "saaremaa", "saaremaa", "kuressaare", "muhu", "ruhnu", "abruka", "vilsandi", "eesti",
    "aste", "leisi", "kihelkonna", "pilguse", "taritu", "orissaare", "kärla", "salme", "valjala",
    "laimjala", "mustjala", "tornimäe", "nasva", "sõrve", "lümanda", "pöide", "kaali", "karja",
    "angla", "torgu", "kuivastu", "koguva", "panga", "asva", "sandla", "eikla", "pärsama",
}


def _keep_upper(w: str) -> bool:
    return w in _ACRONYMS or (len(w) > 1 and _ROMAN.match(w) is not None)


def fix_caps(title: str) -> str:
    """Suurtähtedega pealkirjad lausekujule: "NÄLJAMÄNGUD. LÕIKUSPÄEVA PÄIKESETÕUS"
    → "Näljamängud. Lõikuspäeva päikesetõus".

    - Täielikult suurtähtedega pealkiri muudetakse väiketähtedeks (v.a lühendid ja kohanimed).
    - Segapealkirjas: üksik SUURTÄHTSÕNA → väiketähed ("Taritu JÕULUPIDU" → "Taritu jõulupidu"),
      mitu järjestikust SUURTÄHTSÕNA on tõenäoliselt nimi → suur algustäht ("JOHAN RANDVERE" → "Johan Randvere").
    """
    letters = [c for c in title if c.isalpha()]
    if not letters:
        return title
    mostly_upper = sum(c.isupper() for c in letters) / len(letters) > 0.7
    words = list(_WORD.finditer(title))
    is_caps = [w.group(0).isupper() and len(w.group(0)) > 1 and not _keep_upper(w.group(0)) for w in words]

    out, pos = [], 0
    for i, m in enumerate(words):
        w = m.group(0)
        out.append(title[pos:m.start()])
        pos = m.end()
        if not is_caps[i]:
            out.append(w)
            continue
        low = w.lower()
        if low in _PLACES:
            out.append(low.capitalize())
        elif not mostly_upper and ((i > 0 and is_caps[i - 1]) or (i + 1 < len(words) and is_caps[i + 1])):
            out.append(low.capitalize())     # nimi, nt JOHAN RANDVERE
        else:
            out.append(low)
    out.append(title[pos:])
    s = "".join(out)

    up = lambda m: m.group(1) + m.group(2).upper()
    # pealkirja esimene täht (ka emotikonide järel)
    s = re.sub(r"^([^\w]*)([^\W\d_])", up, s)
    # uus lause — ainult tavalise sõna järel (mitte "40." ega "I.")
    s = re.sub(r"((?<=[a-zäöõüšž])[.!?]\s+)([^\W\d_])", up, s)
    # jutumärkides pealkiri
    s = re.sub(r"([„“\"«]\s*)([^\W\d_])", up, s)
    # spordiklubide jm lühendid alati suurtähtedega
    s = _ALWAYS_UPPER.sub(lambda m: m.group(1).upper(), s)
    return s


def fmt_dt(dt: datetime | date, all_day: bool = False) -> str:
    if isinstance(dt, datetime):
        if dt.tzinfo:
            dt = dt.astimezone(TZ)
        return dt.strftime("%Y-%m-%d") if all_day else dt.strftime("%Y-%m-%dT%H:%M")
    return dt.strftime("%Y-%m-%d")


ET_MONTHS = {
    "jaanuar": 1, "veebruar": 2, "märts": 3, "aprill": 4, "mai": 5, "juuni": 6,
    "juuli": 7, "august": 8, "september": 9, "oktoober": 10, "november": 11, "detsember": 12,
}


def infer_year(month: int, day: int, ref: date | None = None) -> int:
    """Aasta, kui allikas seda ei näita: kui kuupäev on juba möödas, siis järgmine aasta."""
    ref = ref or today()
    try:
        cand = date(ref.year, month, day)
    except ValueError:
        return ref.year
    return ref.year + 1 if cand < ref - timedelta(days=1) else ref.year
