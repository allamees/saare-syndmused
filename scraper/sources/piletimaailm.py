"""piletimaailm.com — Kuressaare Teatri etendused.

Otsingulehelt võtame lavastuste lingid ja iga lavastuse lehelt etendused,
mis toimuvad Saare maakonnas (paljud lavastused tuuritavad üle Eesti).
Leht on Cloudflare'i taga, seega teeme vähe päringuid ja aeglaselt.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..common import Event, clean_text, get
from .piletilevi import SAARE_PLACES

NAME = "piletimaailm.com"
SEARCH = ("https://www.piletimaailm.com/performances/search?name=&performance%5Bfull_name_et%5D="
          "&venue%5Bname%5D=Kuressaare+Teater&from=&to=&commit=Otsi")


def fetch() -> list[Event]:
    soup = BeautifulSoup(get(SEARCH).text, "lxml")
    shows = []
    for div in soup.select("div.event"):
        a = div.select_one(".event-title a")
        if not a:
            continue
        prices = div.select_one(".price-desc")
        price = ""
        if prices and (s := prices.select_one("strong")):
            price = clean_text(s.get_text())
        shows.append((clean_text(a.get_text()), a["href"], price))

    out: list[Event] = []
    for title, href, price in shows:
        try:
            page = BeautifulSoup(get(href, delay=2.0).text, "lxml")
        except Exception as e:  # üks lavastus ei tohi kogu allikat katki teha
            print(f"    ! {href}: {e}")
            continue
        desc_el = page.select_one(".event-description, .description, #event_description")
        desc = clean_text(desc_el.get_text("\n"), 400) if desc_el else ""
        img_el = page.select_one("meta[property='og:image']")
        img = img_el["content"] if img_el else ""
        for row in page.select("#event_performances .event"):
            text = clean_text(row.get_text(" "))
            m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\s+(\d{1,2}):(\d{2})", text)
            if not m:
                continue
            if not SAARE_PLACES.search(text):
                continue
            d, mo, y, hh, mm = m.groups()
            venue = "Kuressaare Teater"
            vm = re.search(r"(Kuressaare[^|,\n]*?(?:Teater|saal|Kultuurikeskus)[^|,\n]*)", text, re.I)
            if vm:
                venue = vm.group(1).strip()
            link = row.select_one("a[href*='/performances/'], a[href*='/orders/']")
            out.append(Event(
                title=(title[0] + title[1:].lower()) if title.isupper() else title,
                start=f"{y}-{mo}-{d}T{int(hh):02d}:{mm}",
                url=href,
                source=NAME,
                location=venue,
                price=price,
                image=img,
                description=desc,
                raw_categories=["Teater"],
            ))
    return out
