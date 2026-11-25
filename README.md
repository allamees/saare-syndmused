# Saare sündmused

Pere ühine kalender, mis koondab Saare maakonna sündmused mitmest allikast ühte kohta ja liigitab need kategooriatesse.
Töötab **Android-telefonis** ja **Windowsi arvutis** paigaldatava veebirakendusena (PWA). Poest pole vaja midagi laadida, jagamiseks piisab lingist.

## Kuidas see töötab

```
allikad (veebilehed, iCal, API-d)
        │   scraper/  (Python)
        ▼
  app/events.json   ← ühtne nimekiri, kategooriad, duplikaadid ühendatud
        │
        ▼
  app/  (rakendus: index.html + app.js)  →  telefon / arvuti
```

## Allikad

| Allik | Kuidas loetakse | Märkus |
|---|---|---|
| saare.events | HTML | Peamine allikas. Samu andmeid näitavad ka **kadi.ee**, **minusaaremaa.ee** ja **visitsaaremaa.ee**, seega on need sellega kaetud. Sisaldab ka kinokava. |
| saaresport.ee | iCal-voog | Spordivõistlused |
| saaremaaspordikool.ee | iCal-voog | „SULETUD“ jms kirjed jäetakse välja |
| kultuurivara.ee | REST API | |
| piletilevi.ee | otsingu-API | Ainult Saare maakonna toimumiskohad. Piirab päringute sagedust (vt allpool). |
| piletimaailm.com | HTML | Kuressaare Teatri etendused, ainult Saaremaal toimuvad |
| Saaremaa Teataja | PDF | Valla kuine infoleht. Viimane number leitakse lehelt saaremaavald.ee/vallaleht ja sündmused loetakse rubriigist „Kultuuri- ja spordisündmused“. Sealt tuleb palju külade rahvamajade sündmusi. Kui lehe küljendus muutub, võib lugemine ebaõnnestuda ja siis tuleb parserit (`scraper/sources/teataja.py`) kohandada. |
| **lisasundmused.txt** | käsitsi | Sinu enda lisatud üritused (nt Facebookist nähtud). Vt allpool. |
| saaremaavald.ee/sundmused | — | **Pole veel lisatud**: valla liides lubab päringuid ainult valla enda lehelt. |
| Facebooki sündmused | — | **Ei ole võimalik**: Facebook nõuab sisselogimist ja keelab automaatse kogumise. |

Kui sama sündmus esineb mitmes allikas (sama pealkiri ja kuupäev), ühendatakse need üheks. Detailvaates on siis näha kõik allikad.

## Sündmuste käsitsi lisamine (nt Facebookist)

Ava fail **`lisasundmused.txt`** ja lisa iga sündmuse jaoks üks rida:

```
Kuupäev | Kell | Nimi | Koht | Link | Hind
12.12.2026 | 19:00 | Jõulukontsert | Leisi rahvamaja | https://www.facebook.com/events/123 | 10 €
19.12.2026 |       | Jõululaat     | Orissaare kultuurimaja |  | Tasuta
```

- Kohustuslikud on ainult kuupäev ja nimi. Kellaaja võid jätta tühjaks, siis on sündmus kogu päeva. Kellaaeg võib olla ka vahemik, näiteks `18:00-20:00`. Mitmepäevase sündmuse kuupäev kirjuta kujul `5.12.2026-7.12.2026`.
- Kui sama sündmus on juba mõnes teises allikas, ühendatakse need. Sinu pealkiri ja kellaaeg jäävad kehtima.
- Möödunud sündmusi ei pea kustutama, need kaovad rakendusest ise.
- Vigane rida jäetakse vahele ja uuenduse logis näed, mis real viga oli.
- **GitHubis** saad faili muuta otse veebis, ka telefonist: ava fail ja vajuta pliiatsi ikooni ✏️, seejärel „Commit changes“. Rakendus uueneb mõne minuti pärast.

## Kategooriad

🎵 Muusika · 🎭 Teater ja tants · 🎬 Film · 🖼️ Näitus ja kunst · ⚽ Sport ja liikumine · 🎉 Pidu ja festival · 🛍️ Laat ja toit · 📚 Koolitus ja loeng · 🧸 Lastele ja peredele · 📌 Muu

Liigituse aluseks on allika enda kategooriad, mida täiendavad pealkirja märksõnad (fail `scraper/categorize.py`). Üks sündmus võib kuuluda mitmesse kategooriasse.

## Kasutamine oma arvutis

- **`uuenda.bat`** kogub sündmused uuesti. Esimesel käivitusel paigaldab see ka vajalikud teegid.
- **`ava.bat`** avab rakenduse brauseris aadressil http://localhost:8765.

## Jagamine perega (tasuta, uueneb iga päev automaatselt)

1. Loo konto lehel https://github.com (kui sul seda veel pole).
2. Loo uus repositoorium, näiteks `saare-syndmused` (Public).
3. Lae selle kausta sisu repositooriumisse üles. Kaust `.venv` jäta välja.
   Lihtsaim viis on GitHub Desktop või lehel „Add file → Upload files“.
4. Ava repositooriumis **Settings → Pages → Source: GitHub Actions**.
5. Ava **Actions → „Uuenda sündmusi“ → Run workflow**.
6. Mõne minuti pärast on rakendus aadressil `https://<kasutajanimi>.github.io/saare-syndmused/`. Saada see link pereliikmetele.

Edaspidi kogub GitHub sündmused ise igal hommikul kell 6–7 ja sinu arvuti ei pea selleks sees olema.

### Paigaldamine

- **Android:** ava link Chrome'is ja vali menüüst ⋮ **„Lisa avakuvale“** või **„Installi rakendus“**.
- **Windows:** ava link Edge'is või Chrome'is ja klõpsa aadressiribal paigaldamise ikoonil (või rakenduse ⬇️ nupul).

## Rakenduse võimalused

- Ajafiltrid: täna, homme, nädalavahetus, 7 päeva, 30 päeva ja lemmikud.
- Kategooriafiltrid, mida saab kombineerida.
- Otsing pealkirja, koha ja kirjelduse järgi.
- Nimekirja- ja kuuvaade.
- Pikemad näitused on koondatud eraldi plokki, et need ei täidaks iga päeva nimekirja.
- ⭐ Lemmikud salvestatakse seadmesse.
- 📆 „Lisa kalendrisse“ laadib alla .ics-faili, mis sobib Google'i, Outlooki ja telefoni kalendrisse.
- 🔗 „Jaga“ saadab sündmuse lingi näiteks WhatsAppi või Messengeri kaudu.
- Töötab ka ilma internetita, näidates viimati laaditud andmeid.

## Teadaolevad piirangud

- **piletilevi.ee** blokeerib liiga sagedasi päringuid (vastus 403). Kogumine on seetõttu aeglane ja väikese päringute arvuga. Kui allikas mingil päeval ei vasta, on see rakenduse jaluses tähistatud ⚠️ märgiga ning teised allikad töötavad edasi.
- **saare.events** ei näita alati aastat. Kui kuupäev on juba möödas, eeldatakse järgmist aastat.
- Kinokava (🎬) sisaldab palju seansse. Kui see segab, saab filtriga valida ainult soovitud kategooriad. Valik jääb meelde.

## Uue allika lisamine

1. Loo fail `scraper/sources/<nimi>.py` funktsiooniga `fetch()`, mis tagastab `Event`-objektide nimekirja.
2. Lisa see faili `scraper/run.py` loendisse `SOURCES`.
