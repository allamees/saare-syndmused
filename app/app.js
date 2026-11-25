"use strict";
/* Saare sündmused — kliendirakendus (PWA). Andmed tulevad failist events.json. */

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* privaatrežiim */ } },
};

const DATE_FILTERS = [
  ["all", "Kõik"],
  ["today", "Täna"],
  ["tomorrow", "Homme"],
  ["weekend", "Nädalavahetus"],
  ["week", "7 päeva"],
  ["month", "30 päeva"],
  ["fav", "★ Lemmikud"],
];
const LONG_DAYS = 7; // sellest pikemad sündmused (näitused) eraldi plokki

const state = {
  data: null,
  events: [],
  cats: new Map(),
  q: "",
  date: store.get("date", "all"),
  selCats: new Set(store.get("cats", [])),
  onlyKuressaare: store.get("kuressaare", false),
  view: store.get("view", "list"),
  favs: new Set(store.get("favs", [])),
  month: null,
  selDay: null,
  limit: 120,
};

/* ---------- kuupäevad ---------- */
const pad = (n) => String(n).padStart(2, "0");
const dayKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const parseDay = (s) => { const [y, m, d] = s.slice(0, 10).split("-").map(Number); return new Date(y, m - 1, d); };
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const todayDate = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
const daysBetween = (a, b) => Math.round((b - a) / 86400000);
const fmtDay = new Intl.DateTimeFormat("et-EE", { weekday: "long", day: "numeric", month: "long" });
const fmtShort = new Intl.DateTimeFormat("et-EE", { day: "numeric", month: "numeric" });
const fmtMonth = new Intl.DateTimeFormat("et-EE", { month: "long", year: "numeric" });
const fmtFull = new Intl.DateTimeFormat("et-EE", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
const timeOf = (s) => (s && s.length > 10 ? s.slice(11, 16) : "");

/* ---------- riigipühad ja rahvakalendri tähtpäevad ---------- */
// [kuu, päev, nimi, riigipüha?]
const FIXED_DAYS = [
  [1, 1, "uusaasta", true],
  [1, 6, "kolmekuningapäev", false],
  [1, 25, "tõnisepäev", false],
  [2, 2, "küünlapäev", false],
  [2, 24, "iseseisvuspäev", true],
  [2, 24, "madisepäev", false],
  [3, 25, "paastumaarjapäev", false],
  [4, 23, "jüripäev", false],
  [5, 1, "kevadpüha", true],
  [5, 1, "volbripäev", false],
  [6, 23, "võidupüha", true],
  [6, 23, "jaanilaupäev", false],
  [6, 24, "jaanipäev", true],
  [6, 29, "peetripäev", false],
  [8, 10, "lauritsapäev", false],
  [8, 20, "taasiseseisvumispäev", true],
  [8, 24, "pärtlipäev", false],
  [9, 29, "mihklipäev", false],
  [11, 2, "hingedepäev", false],
  [11, 10, "mardipäev", false],
  [11, 25, "kadripäev", false],
  [12, 21, "toomapäev", false],
  [12, 24, "jõululaupäev", true],
  [12, 25, "esimene jõulupüha", true],
  [12, 26, "teine jõulupüha", true],
];

function easter(y) { // Gregoriuse kalendri lihavõtted (Meeus/Jones/Butcher)
  const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4;
  const f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31), day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(y, month - 1, day);
}

const holidayCache = new Map();
function holidaysOfYear(y) {
  if (holidayCache.has(y)) return holidayCache.get(y);
  const map = new Map();
  const add = (d, name, isState) => {
    const k = dayKey(d);
    if (!map.has(k)) map.set(k, []);
    map.get(k).push({ name, state: isState });
  };
  for (const [m, d, name, st] of FIXED_DAYS) add(new Date(y, m - 1, d), name, st);
  const E = easter(y);
  add(addDays(E, -47), "vastlapäev", false);
  add(addDays(E, -2), "suur reede", true);
  add(E, "ülestõusmispühade 1. püha", true);
  add(addDays(E, 49), "nelipühade 1. püha", true);
  holidayCache.set(y, map);
  return map;
}
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const holidaysOn = (d) => (holidaysOfYear(d.getFullYear()).get(dayKey(d)) || []).map((h) => ({ ...h, name: cap(h.name) }));

function dayLabel(d) {
  const hol = holidaysOn(d);
  return esc(fmtDay.format(d)) +
    (hol.length ? ` <span class="hol">· ${esc(hol.map((h) => h.name).join(", "))}</span>` : "");
}

function prepare(e) {
  e._s = parseDay(e.start);
  e._e = e.end ? parseDay(e.end) : e._s;
  e._len = daysBetween(e._s, e._e);
  e._text = `${e.title} ${e.location} ${e.description}`.toLowerCase();
  return e;
}

function dateRange(kind) {
  const t = todayDate();
  switch (kind) {
    case "today": return [t, t];
    case "tomorrow": return [addDays(t, 1), addDays(t, 1)];
    case "weekend": {
      const dow = t.getDay(); // 0=P
      if (dow === 0) return [t, t];
      const sat = addDays(t, 6 - dow);
      return [dow === 6 ? t : (dow === 5 ? t : sat), addDays(sat, 1)];
    }
    case "week": return [t, addDays(t, 6)];
    case "month": return [t, addDays(t, 29)];
    default: return [t, addDays(t, 400)];
  }
}

/* ---------- filtreerimine ---------- */
function matchesBase(e) {
  if (state.onlyKuressaare && !e.kuressaare) return false;
  if (state.selCats.size && !e.categories.some((c) => state.selCats.has(c))) return false;
  // "Kõik" ei sisalda kinoseansse (ainult filmi-kategooriaga sündmused) — need on eraldi "Film" all.
  // Erand: otsing ja lemmikud näitavad ka filme.
  if (!state.selCats.size && !state.q && state.date !== "fav" &&
      e.categories.length === 1 && e.categories[0] === "film") return false;
  if (state.q) {
    const words = state.q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.every((w) => e._text.includes(w))) return false;
  }
  return true;
}

function filtered() {
  let list = state.events.filter(matchesBase);
  if (state.date === "fav") return list.filter((e) => state.favs.has(e.id));
  const [from, to] = dateRange(state.date);
  return list.filter((e) => e._e >= from && e._s <= to);
}

/* ---------- renderdamine ---------- */
/* Üks rida: "12:00 Pealkiri - Koht · Hind" */
function cardHTML(e) {
  const t = e.all_day ? "" : timeOf(e.start);
  const extra = [];
  if (e._len > 0) extra.push(`kuni ${fmtShort.format(e._e)}`);
  if (e.price) extra.push(esc(e.price));
  // teatrietenduse puhul eraldajaks 🎭, muidu "-"
  const sep = e.theatre ? `<span class="theatre" title="Teatrietendus">🎭</span>` : (e.location ? " - " : "");
  const rest = (e.location ? esc(e.location) : "") + (extra.length ? ` · ${extra.join(" · ")}` : "");
  const fav = state.favs.has(e.id);
  return `<div class="card" role="button" tabindex="0" data-id="${e.id}">
    <span class="time">${t}</span>
    <span class="line"><span class="title">${esc(e.title)}</span>${sep}<span class="meta">${rest}</span></span>
    <button class="star ${fav ? "on" : ""}" data-fav="${e.id}" aria-label="${fav ? "Eemalda lemmikutest" : "Lisa lemmikutesse"}">${fav ? "★" : "☆"}</button>
  </div>`;
}

function renderList() {
  const el = $("#listView");
  const list = filtered();
  if (!list.length) {
    el.innerHTML = `<p class="status">${state.date === "fav" ? "Lemmikuid veel pole — vajuta sündmuse juures ☆." : "Selliseid sündmusi ei leitud."}</p>`;
    return;
  }
  const [from] = state.date === "fav" ? [todayDate()] : dateRange(state.date);
  // pikad / juba alanud sündmused eraldi
  const ongoing = list.filter((e) => e._s < from || e._len >= LONG_DAYS);
  const regular = list.filter((e) => !(e._s < from || e._len >= LONG_DAYS));
  let html = "";
  if (ongoing.length) {
    html += `<details class="ongoing"><summary>Käimasolevad näitused ja pikemad sündmused (${ongoing.length})</summary>
      ${ongoing.sort((a, b) => a._e - b._e).map((e) => cardHTML(e)).join("")}</details>`;
  }
  const t = dayKey(todayDate());
  let lastDay = "";
  regular.slice(0, state.limit).forEach((e) => {
    const k = dayKey(e._s);
    if (k !== lastDay) {
      lastDay = k;
      const label = (k === t ? "täna · " : (k === dayKey(addDays(todayDate(), 1)) ? "homme · " : "")) + dayLabel(e._s);
      html += `<h3 class="day-head ${k === t ? "today" : ""}">${label}</h3>`;
    }
    html += cardHTML(e);
  });
  if (regular.length > state.limit) {
    html += `<p style="text-align:center"><button class="btn" id="moreBtn">Näita rohkem (${regular.length - state.limit})</button></p>`;
  }
  el.innerHTML = html;
}

function renderMonth() {
  const el = $("#monthView");
  if (!state.month) {
    const t = todayDate();
    state.month = new Date(t.getFullYear(), t.getMonth(), 1);
    state.selDay = state.selDay || dayKey(t);
  }
  const m = state.month;
  const first = new Date(m.getFullYear(), m.getMonth(), 1);
  const start = addDays(first, -((first.getDay() + 6) % 7)); // esmaspäevast
  const list = state.events.filter(matchesBase).filter((e) => state.date !== "fav" || state.favs.has(e.id));
  const byDay = new Map();
  for (const e of list) {
    if (e._len >= LONG_DAYS) continue;
    for (let d = new Date(e._s); d <= e._e; d = addDays(d, 1)) {
      const k = dayKey(d);
      if (!byDay.has(k)) byDay.set(k, []);
      byDay.get(k).push(e);
    }
  }
  const t = dayKey(todayDate());
  let html = `<div class="month-nav">
    <button class="btn" data-mnav="-1" aria-label="Eelmine kuu">‹</button>
    <h2>${fmtMonth.format(m)}</h2>
    <button class="btn" data-mnav="1" aria-label="Järgmine kuu">›</button></div>
    <div class="grid">${["E", "T", "K", "N", "R", "L", "P"].map((d) => `<div class="wd">${d}</div>`).join("")}`;
  for (let i = 0; i < 42; i++) {
    const d = addDays(start, i);
    const k = dayKey(d);
    const evs = byDay.get(k) || [];
    const hol = holidaysOn(d);
    const cls = ["cell", d.getMonth() !== m.getMonth() ? "other" : "", k === t ? "today" : "", k === state.selDay ? "sel" : "",
      hol.some((h) => h.state) ? "holiday" : ""].join(" ");
    html += `<button class="${cls}" data-day="${k}" ${hol.length ? `title="${esc(hol.map((h) => h.name).join(", "))}"` : ""}>
      <span class="d">${d.getDate()}</span>
      ${evs.length ? `<span class="cnt">${evs.length} sündm.</span>` : ""}</button>`;
    if (i === 34 && addDays(start, 35).getMonth() !== m.getMonth()) break;
  }
  html += `</div><div id="dayList"></div>`;
  el.innerHTML = html;
  if (state.selDay) renderDayList(state.selDay, byDay.get(state.selDay) || [], list);
}

function renderDayList(k, evs, list) {
  const d = parseDay(k);
  const long = list.filter((e) => e._len >= LONG_DAYS && e._s <= d && e._e >= d);
  $("#dayList").innerHTML = `<h3 class="day-head" style="position:static">${dayLabel(d)}</h3>` +
    (evs.length ? evs.sort((a, b) => a.start.localeCompare(b.start)).map((e) => cardHTML(e)).join("") : `<p class="status">Sel päeval sündmusi pole.</p>`) +
    (long.length ? `<details class="ongoing"><summary>Samal ajal avatud näitused (${long.length})</summary>${long.map((e) => cardHTML(e)).join("")}</details>` : "");
}

function renderChips() {
  $("#dateChips").innerHTML = DATE_FILTERS.map(([k, l]) =>
    `<button class="chip" data-date="${k}" aria-pressed="${state.date === k}">${l}</button>`).join("") +
    `<span class="chip-sep" aria-hidden="true"></span>` +
    `<button class="chip" data-place="kuressaare" aria-pressed="${state.onlyKuressaare}" title="Näita ainult Kuressaares toimuvaid sündmusi">Kuressaare</button>`;
  const counts = new Map();
  for (const e of state.events) {
    if (state.onlyKuressaare && !e.kuressaare) continue;
    for (const c of e.categories) counts.set(c, (counts.get(c) || 0) + 1);
  }
  $("#catChips").innerHTML = `<button class="chip" data-cat="" aria-pressed="${state.selCats.size === 0}">Kõik</button>` +
    [...state.cats.values()].filter((c) => counts.get(c.key)).map((c) =>
      `<button class="chip" data-cat="${c.key}" aria-pressed="${state.selCats.has(c.key)}">${esc(c.label)}<span class="n">${counts.get(c.key)}</span></button>`).join("");
}

function render() {
  renderChips();
  $("#listView").hidden = state.view !== "list";
  $("#monthView").hidden = state.view !== "month";
  $("#viewBtn").textContent = state.view === "list" ? "Kuu" : "Nimekiri";
  $("#viewBtn").title = state.view === "list" ? "Kuuvaade" : "Nimekiri";
  if (state.view === "list") renderList(); else renderMonth();
  document.documentElement.style.setProperty("--head-h", $(".top").offsetHeight + "px");
}

function renderFoot() {
  const d = state.data;
  const gen = d.generated ? new Date(d.generated) : null;
  const src = d.sources.filter((s) => s.url || s.count).map((s) =>
    (s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener" class="${s.ok ? "" : "bad"}">${esc(s.name)}</a>` : esc(s.name)) +
    (s.ok ? "" : " (ei vastanud)")).join(", ");
  $("#foot").innerHTML = `<p>Uuendatud: ${gen ? gen.toLocaleString("et-EE", { dateStyle: "medium", timeStyle: "short" }) : "?"} · ${state.events.length} sündmust</p>
    <p>Allikad: ${src}. Andmed on koondatud avalikelt lehtedelt — täpsema info ja piletid leiad alati algallikast.</p>`;
}

/* ---------- detailvaade ---------- */
function whenText(e) {
  const t1 = e.all_day ? "" : timeOf(e.start);
  if (e._len > 0) return `${fmtFull.format(e._s)}${t1 ? " " + t1 : ""} – ${fmtFull.format(e._e)}${timeOf(e.end) ? " " + timeOf(e.end) : ""}`;
  const t2 = e.end && !e.all_day ? timeOf(e.end) : "";
  return `${fmtFull.format(e._s)}${t1 ? ", kell " + t1 : ""}${t2 && t2 !== t1 ? "–" + t2 : ""}`;
}

function openDetail(id, push = true) {
  const e = state.events.find((x) => x.id === id);
  if (!e) return;
  const fav = state.favs.has(e.id);
  const cats = e.categories.map((c) => esc(state.cats.get(c)?.label || "")).join(", ");
  $("#detailBody").innerHTML = `
    <button class="close" data-close aria-label="Sulge">✕</button>
    ${e.image ? `<img src="${esc(e.image)}" alt="" loading="lazy" onerror="this.remove()">` : `<div style="height:48px"></div>`}
    <div class="body">
      <h2>${esc(e.title)}</h2>
      <div class="row"><b>Aeg</b><span>${esc(whenText(e))}</span></div>
      ${e.location ? `<div class="row"><b>Koht</b><span>${esc(e.location)}</span></div>` : ""}
      ${e.price ? `<div class="row"><b>Hind</b><span>${esc(e.price)}</span></div>` : ""}
      <div class="row"><b>Liik</b><span>${cats}</span></div>
      ${e.description ? `<div class="desc">${esc(e.description)}</div>` : ""}
      <div class="actions">
        ${e.sources.filter((s) => s.url).map((s, i) => `<a class="btn ${i === 0 ? "primary" : ""}" href="${esc(s.url)}" target="_blank" rel="noopener">${i === 0 ? "Vaata lähemalt" : "Ka"}: ${esc(s.name)}</a>`).join("")}
        <button class="btn" data-ics="${e.id}">Lisa kalendrisse</button>
        <button class="btn" data-share="${e.id}">Jaga</button>
        <button class="btn" data-fav="${e.id}">${fav ? "★ Lemmik" : "☆ Lemmikuks"}</button>
      </div>
    </div>`;
  const dlg = $("#detail");
  if (!dlg.open) dlg.showModal();
  dlg.scrollTop = 0;
  if (push && location.hash !== "#e=" + id) history.pushState(null, "", "#e=" + id);
}

function closeDetail() {
  const dlg = $("#detail");
  if (dlg.open) dlg.close();
  if (location.hash.startsWith("#e=")) history.pushState(null, "", location.pathname + location.search);
}

function icsFor(e) {
  const fold = (s) => s.replace(/([,;\\])/g, "\\$1").replace(/\n/g, "\\n");
  const dt = (s, allDay, plusDay) => {
    if (allDay) { const d = plusDay ? addDays(parseDay(s), 1) : parseDay(s); return `;VALUE=DATE:${dayKey(d).replace(/-/g, "")}`; }
    return `;TZID=Europe/Tallinn:${s.replace(/[-:]/g, "").slice(0, 13)}00`;
  };
  const allDay = e.all_day || !timeOf(e.start);
  const link = (e.sources.find((s) => s.url) || {}).url || "";
  let end = e.end;
  if (!end) end = allDay ? e.start.slice(0, 10) : null;
  const lines = [
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Saare syndmused//ET", "BEGIN:VEVENT",
    `UID:${e.id}@saare-syndmused`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").slice(0, 15)}Z`,
    `DTSTART${dt(e.start, allDay)}`,
    end ? `DTEND${dt(allDay ? end.slice(0, 10) : end, allDay, allDay)}` : `DURATION:PT2H`,
    `SUMMARY:${fold(e.title)}`,
    e.location ? `LOCATION:${fold(e.location)}` : "",
    `DESCRIPTION:${fold((e.description || "") + (link ? (e.description ? "\n\n" : "") + link : ""))}`,
    link ? `URL:${link}` : "",
    "END:VEVENT", "END:VCALENDAR",
  ].filter(Boolean);
  return lines.join("\r\n");
}

function downloadIcs(e) {
  const blob = new Blob([icsFor(e)], { type: "text/calendar;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = e.title.replace(/[^\p{L}\p{N}]+/gu, "-").slice(0, 40) + ".ics";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

async function share(e) {
  const url = location.origin + location.pathname + "#e=" + e.id;
  const text = `${e.title} — ${whenText(e)}${e.location ? ", " + e.location : ""}`;
  if (navigator.share) {
    try { await navigator.share({ title: e.title, text, url }); } catch { /* katkestati */ }
  } else {
    try { await navigator.clipboard.writeText(`${text}\n${url}`); alert("Link kopeeritud!"); } catch { prompt("Kopeeri link:", url); }
  }
}

function toggleFav(id) {
  if (state.favs.has(id)) state.favs.delete(id); else state.favs.add(id);
  store.set("favs", [...state.favs]);
}

/* ---------- sündmused ---------- */
document.addEventListener("click", (ev) => {
  const t = ev.target.closest("[data-fav],[data-date],[data-place],[data-cat],[data-day],[data-mnav],[data-ics],[data-share],[data-close],#moreBtn,#viewBtn,.card");
  if (!t) return;
  if (t.dataset.fav) {
    ev.stopPropagation();
    toggleFav(t.dataset.fav);
    if ($("#detail").open) openDetail(t.dataset.fav, false);
    render();
  } else if (t.dataset.date) {
    state.date = t.dataset.date; state.limit = 120; store.set("date", state.date); render(); window.scrollTo(0, 0);
  } else if (t.dataset.place) {
    state.onlyKuressaare = !state.onlyKuressaare; store.set("kuressaare", state.onlyKuressaare); state.limit = 120; render();
  } else if (t.dataset.cat !== undefined) {
    const c = t.dataset.cat;
    // korraga ainult üks kategooria; sama uuesti klõpsates → "Kõik"
    const wasSelected = state.selCats.has(c);
    state.selCats.clear();
    if (c && !wasSelected) state.selCats.add(c);
    store.set("cats", [...state.selCats]); state.limit = 120; render();
  } else if (t.dataset.day) {
    state.selDay = t.dataset.day; renderMonth(); $("#dayList").scrollIntoView({ behavior: "smooth", block: "start" });
  } else if (t.dataset.mnav) {
    state.month = new Date(state.month.getFullYear(), state.month.getMonth() + Number(t.dataset.mnav), 1); state.selDay = null; renderMonth();
  } else if (t.dataset.ics) {
    downloadIcs(state.events.find((x) => x.id === t.dataset.ics));
  } else if (t.dataset.share) {
    share(state.events.find((x) => x.id === t.dataset.share));
  } else if (t.hasAttribute("data-close")) {
    closeDetail();
  } else if (t.id === "moreBtn") {
    state.limit += 150; renderList();
  } else if (t.id === "viewBtn") {
    state.view = state.view === "list" ? "month" : "list"; store.set("view", state.view); render();
  } else if (t.classList.contains("card")) {
    openDetail(t.dataset.id);
  }
});
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter" && ev.target.classList?.contains("card")) openDetail(ev.target.dataset.id);
});
$("#detail").addEventListener("click", (ev) => { if (ev.target === ev.currentTarget) closeDetail(); });
$("#detail").addEventListener("cancel", (ev) => { ev.preventDefault(); closeDetail(); });
let qTimer;
$("#search").addEventListener("input", (ev) => {
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { state.q = ev.target.value.trim(); state.limit = 120; render(); }, 150);
});
window.addEventListener("popstate", () => {
  const m = location.hash.match(/^#e=(\w+)/);
  if (m) openDetail(m[1], false); else if ($("#detail").open) $("#detail").close();
});

// Paigaldamise nupp (Android Chrome / Windows Edge)
let installEvt = null;
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); installEvt = e; $("#installBtn").hidden = false; });
$("#installBtn").addEventListener("click", async () => {
  if (!installEvt) return;
  installEvt.prompt(); await installEvt.userChoice; installEvt = null; $("#installBtn").hidden = true;
});

/* ---------- käivitus ---------- */
async function load() {
  try {
    const r = await fetch("events.json", { cache: "no-cache" });
    if (!r.ok) throw new Error(r.status);
    const data = await r.json();
    state.data = data;
    state.cats = new Map(data.categories.map((c) => [c.key, c]));
    state.events = data.events.map(prepare);
    // kategooriad võivad muutuda — eemalda salvestatud valikust olematud
    state.selCats = new Set([...state.selCats].filter((c) => state.cats.has(c)));
    store.set("cats", [...state.selCats]);
    // eemalda lemmikutest juba möödunud sündmused
    const ids = new Set(state.events.map((e) => e.id));
    state.favs = new Set([...state.favs].filter((id) => ids.has(id)));
    store.set("favs", [...state.favs]);
    $("#status").textContent = "";
    renderFoot();
    render();
    const m = location.hash.match(/^#e=(\w+)/);
    if (m) openDetail(m[1], false);
  } catch (err) {
    $("#status").textContent = "Sündmuste laadimine ebaõnnestus. Kontrolli internetiühendust ja proovi uuesti.";
    console.error(err);
  }
}
load();

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
