/* Stadium Surge frontend. Calls the Flask API; if the API is unreachable it falls back
   to pre-computed demo data (fallback.js) so the walkthrough always works. */
const S = { meta: null, plan: null, lang: "gu", filter: "all", charts: {}, demo: false };
const $ = (id) => document.getElementById(id);
const fmt = (n) => (typeof n === "number" ? n.toLocaleString("en-IN") : n);

async function api(path, opts, fbKey) {
  try {
    const r = await fetch(path, opts);
    if (!r.ok) throw new Error((await r.json()).error || r.status);
    return await r.json();
  } catch (e) {
    console.warn("API failed, using demo data:", path, e);
    setDemo();
    return (window.FALLBACK || {})[fbKey];
  }
}
function setDemo() {
  if (S.demo) return;
  S.demo = true;
  $("mode").textContent = "● Demo mode (cached results)";
  $("mode").className = "pill demo";
}

/* ---------------- tabs ---------------- */
document.querySelectorAll(".tab").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === b));
    document.querySelectorAll(".tabpane").forEach((p) => p.classList.toggle("active", p.id === "tab-" + b.dataset.tab));
    if (b.dataset.tab === "forecast" && !S.fcLoaded) { S.fcLoaded = true; loadForecast(); loadCalendar(); }
  })
);

/* ---------------- init ---------------- */
async function init() {
  S.meta = await api("/api/meta", null, "meta");
  const m = S.meta;
  $("today").textContent = "Today: " + new Date(m.today).toDateString();
  $("evType").innerHTML = m.event_types.map((t) => `<option>${t}</option>`).join("");
  $("evVenue").innerHTML = Object.entries(m.venues).map(([k, v]) => `<option value="${k}">${v.name}</option>`).join("");
  $("evVenue").value = "NMS";
  $("fcStation").innerHTML = Object.entries(m.stations).map(([k, v]) => `<option value="${k}">${v.name}</option>`).join("");
  $("fcStation").value = "GUJ_UNI";
  $("fcDate").value = "2026-10-17";
  renderMetrics(m.metrics);

  const ev = await api("/api/events", null, "events");
  S.events = ev.upcoming;
  $("evPick").innerHTML += ev.upcoming
    .map((e, i) => `<option value="${i}">${e.date} · ${e.name}</option>`).join("");
  $("evPick").value = String(ev.upcoming.findIndex((e) => e.name.includes("New Zealand")));
  renderUpcoming(ev.upcoming);
  generate();
  const tab = document.querySelector(`[data-tab="${location.hash.slice(1)}"]`);
  if (tab) tab.click();
}

$("evPick").addEventListener("change", () => {
  const e = S.events[$("evPick").value];
  if (!e) return;
  $("evName").value = e.name; $("evType").value = e.event_type; $("evVenue").value = e.venue;
  $("evDate").value = e.date; $("evAtt").value = e.expected_attendance;
  $("evStart").value = e.start_time; $("evEnd").value = e.end_time;
});
$("evType").addEventListener("change", () => {
  const map = { cricket: "NMS", concert: "NMS", navratri: "GMDC", riverfront: "RIVERFRONT" };
  $("evVenue").value = map[$("evType").value];
});
$("btnPlan").addEventListener("click", generate);

async function generate() {
  const body = {
    name: $("evName").value, event_type: $("evType").value, venue: $("evVenue").value, date: $("evDate").value,
    expected_attendance: +$("evAtt").value, start_time: $("evStart").value, end_time: $("evEnd").value,
  };
  $("btnPlan").classList.add("spin"); $("btnPlan").textContent = "Simulating…";
  const p = await api("/api/plan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }, "plan");
  $("btnPlan").classList.remove("spin"); $("btnPlan").textContent = "Generate crowd plan →";
  S.plan = p;
  renderPlan(p);
}

/* ---------------- plan rendering ---------------- */
function renderPlan(p) {
  const s = p.summary;
  $("stName").textContent = s.station_name;
  $("kpis").innerHTML = [
    ["blue", fmt(s.metro_riders), `Metro riders at ${s.station_name}`],
    ["red", fmt(s.peak_arrival_rate) + "/min", "Peak arrival rate (15-min avg)"],
    ["amber", s.surge_headway + " min", "Surge train headway"],
    ["blue", "+" + s.extra_trains, "Extra trains vs normal service"],
    ["red", fmt(s.peak_street_queue), `Peak queue in holding zones (${s.peak_time})`],
    ["green", s.clear_time, `Station clear (${s.clear_minutes_after_end} min after end)`],
    ["amber", "~" + s.max_wait_min + " min", "Worst-case passenger wait"],
    ["blue", fmt(s.staff), "Staff to deploy"],
  ].map(([c, v, l]) => `<div class="kpi ${c}"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");

  $("compare").innerHTML = `
    <div class="cmp bad"><b>❌ Without a plan</b>Paid area peaks at <b style="display:inline">${fmt(s.baseline_peak_inside)}</b> people
      (capacity ${fmt(s.paid_area_capacity)}), overcrowded for <b style="display:inline">${s.baseline_overcrowded_minutes} minutes</b>.
      Clears ${s.baseline_clear_minutes_after_end} min after the event.</div>
    <div class="cmp good"><b>✅ With Stadium Surge plan</b>Paid area capped at ${fmt(s.peak_inside)} (metering). The excess waits safely in
      holding zones. ${s.surge_headway}-min headway with +${s.extra_trains} trains. Clear by ${s.clear_time}.</div>`;

  minuteChart(p.minutes, s.paid_area_capacity);
  renderFilters(p.timeline);
  renderTimeline();
  renderAnnouncements();
  $("others").innerHTML = p.other_stations.length
    ? p.other_stations.map((o) => `<div class="other"><b>${o.name}</b> · ${fmt(o.riders)} riders, peak ${fmt(o.peak_15min)}/15 min<br>${o.advice}</div>`).join("")
    : "<p class='hint'>No secondary station.</p>";
  if (p.forecast) {
    dayChart("dayChart", p.forecast, true);
    $("dayRush").innerHTML = rushChips(p.forecast);
  }
}

function renderFilters(tl) {
  const cats = ["all", ...new Set(tl.map((t) => t.category))];
  $("tlFilters").innerHTML = cats.map((c) => `<button data-c="${c}" class="${c === S.filter ? "active" : ""}">${c}</button>`).join("");
  $("tlFilters").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    S.filter = b.dataset.c; renderFilters(tl); renderTimeline();
  }));
}

function renderTimeline() {
  const tl = S.plan.timeline.filter((t) => S.filter === "all" || t.category === S.filter);
  $("timeline").innerHTML = tl.map((t) => `
    <div class="tl ${t.severity}">
      <div class="t">${t.time}</div>
      <div><span class="tag">${t.category}</span><span class="a">${t.action}</span>
        ${t.detail ? `<div class="d">${t.detail}</div>` : ""}
        ${t.announcement ? `<div class="ann">📢 ${t.announcement[S.lang]}</div>` : ""}
      </div>
    </div>`).join("");
}

document.querySelectorAll(".lang").forEach((b) => b.addEventListener("click", () => {
  S.lang = b.dataset.lang;
  document.querySelectorAll(".lang").forEach((x) => x.classList.toggle("active", x === b));
  renderAnnouncements(); renderTimeline();
}));

function renderAnnouncements() {
  $("annList").innerHTML = S.plan.announcements.map((a, i) => `
    <div class="annc"><div class="h">${a.title}<button class="speak" data-i="${i}">🔊 Play</button></div>
      <p>${a[S.lang]}</p></div>`).join("");
  $("annList").querySelectorAll(".speak").forEach((b) => b.addEventListener("click", () => speak(S.plan.announcements[b.dataset.i][S.lang])));
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = { gu: "gu-IN", hi: "hi-IN", en: "en-IN" }[S.lang];
  const v = speechSynthesis.getVoices().find((v) => v.lang === u.lang) || speechSynthesis.getVoices().find((v) => v.lang.startsWith("hi"));
  if (v) u.voice = v;
  u.rate = 0.95;
  speechSynthesis.speak(u);
}

/* ---------------- charts ---------------- */
function mkChart(id, cfg) {
  if (!window.Chart) return;
  if (S.charts[id]) S.charts[id].destroy();
  S.charts[id] = new Chart($(id), cfg);
}

function minuteChart(mins, cap) {
  mkChart("minuteChart", {
    type: "line",
    data: {
      labels: mins.map((m) => m.time),
      datasets: [
        { label: "Inside station, no plan", data: mins.map((m) => m.baseline_inside), borderColor: "#d62839", backgroundColor: "rgba(214,40,57,.08)", fill: true, pointRadius: 0, borderWidth: 2 },
        { label: "Inside station, with plan", data: mins.map((m) => m.inside), borderColor: "#0b5ed7", backgroundColor: "rgba(11,94,215,.12)", fill: true, pointRadius: 0, borderWidth: 2 },
        { label: "Waiting in holding zones (plan)", data: mins.map((m) => m.street_queue), borderColor: "#e8a317", pointRadius: 0, borderWidth: 2, borderDash: [5, 4] },
        { label: "Arrivals / min ×10", data: mins.map((m) => m.arrivals * 10), borderColor: "#7a7f8f", pointRadius: 0, borderWidth: 1 },
        { label: "Safe capacity", data: mins.map(() => cap), borderColor: "#1a9b5c", pointRadius: 0, borderWidth: 2, borderDash: [2, 3] },
      ],
    },
    options: {
      maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      scales: { x: { ticks: { maxTicksLimit: 14 } }, y: { title: { display: true, text: "people" } } },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } },
    },
  });
}

const LV = { low: "#9fd4ad", moderate: "#b5d86a", high: "#f2b33d", critical: "#d62839" };
function dayChart(id, f, compact) {
  mkChart(id, {
    type: "bar",
    data: {
      labels: f.hours.map((h) => h.label),
      datasets: [
        { label: "Predicted footfall", data: f.hours.map((h) => h.predicted), backgroundColor: f.hours.map((h) => LV[h.level]) },
        { label: "Normal day (no event)", data: f.hours.map((h) => h.baseline), type: "line", borderColor: "#14213d", borderDash: [4, 4], pointRadius: 0, borderWidth: 1.5 },
        { label: "Hourly capacity", data: f.hours.map(() => f.capacity), type: "line", borderColor: "#d62839", pointRadius: 0, borderWidth: 1, borderDash: [2, 3] },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: !compact, position: "bottom" },
        tooltip: { callbacks: { afterLabel: (c) => c.datasetIndex === 0 ? `Load ${f.hours[c.dataIndex].load_pct}% · ${f.hours[c.dataIndex].level}` : "" } } },
      scales: { y: { title: { display: !compact, text: "passengers / hour" } } },
    },
  });
}

function rushChips(f) {
  const r = f.hours.filter((h) => h.level === "high" || h.level === "critical");
  return (r.length ? `<span class="chip">Rush hours:</span>` + r.map((h) => `<span class="chip ${h.level}">${h.label} · ${h.load_pct}%</span>`).join("")
    : `<span class="chip">No rush hours predicted</span>`) + ` <span class="chip">Peak ${f.peak.label} (${fmt(f.peak.predicted)}/hr)</span>`
    + ` <span class="chip">${f.source === "ml" ? "🤖 ML model" : "heuristic"}</span>`;
}

/* ---------------- forecast tab ---------------- */
$("btnFc").addEventListener("click", loadForecast);
$("fcStation").addEventListener("change", () => { loadForecast(); loadCalendar(); });

async function loadForecast() {
  const f = await api(`/api/forecast?station=${$("fcStation").value}&date=${$("fcDate").value}`, null, "forecast");
  dayChart("fcChart", f, false);
  $("fcInfo").innerHTML = `<span class="chip">${f.station_name} · ${f.date}</span>`
    + (f.events && f.events.length ? f.events.map((e) => `<span class="chip high">🎉 ${e}</span>`).join("") : `<span class="chip">No event</span>`)
    + rushChips(f);
}

async function loadCalendar() {
  const c = await api(`/api/rush-calendar?station=${$("fcStation").value}&days=14`, null, "calendar");
  const hours = c.days[0].hours.map((h) => h.label);
  let html = `<div class="heat" style="grid-template-columns:200px repeat(${hours.length},1fr)"><div></div>`
    + hours.map((h) => `<div class="hd">${h.slice(0, 2)}</div>`).join("");
  c.days.forEach((d) => {
    const dt = new Date(d.date);
    html += `<div class="dl" data-d="${d.date}">${dt.toDateString().slice(0, 10)}${d.events.length ? `<small>${d.events[0]}</small>` : ""}</div>`;
    html += d.hours.map((h) => `<div class="c ${h.level}" data-d="${d.date}" title="${d.date} ${h.label}: ${fmt(h.predicted)} pax (${h.level})"></div>`).join("");
  });
  $("heat").innerHTML = html + "</div>";
  $("heat").querySelectorAll("[data-d]").forEach((el) => el.addEventListener("click", () => {
    $("fcDate").value = el.dataset.d; loadForecast(); window.scrollTo({ top: 0, behavior: "smooth" });
  }));
}

function renderUpcoming(list) {
  $("upcoming").innerHTML = `<tr><th>Date</th><th>Event</th><th>Type</th><th>Venue</th><th>Attendance</th><th>Time</th><th></th></tr>`
    + list.map((e, i) => `<tr><td>${e.date}</td><td>${e.name}</td><td>${e.event_type}</td><td>${S.meta.venues[e.venue].name}</td>
      <td>${fmt(e.expected_attendance)}</td><td>${e.start_time}–${e.end_time}</td><td><button data-i="${i}">Plan →</button></td></tr>`).join("");
  $("upcoming").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    $("evPick").value = b.dataset.i; $("evPick").dispatchEvent(new Event("change"));
    document.querySelector('[data-tab="plan"]').click(); generate();
  }));
}

/* ---------------- model tab ---------------- */
function renderMetrics(m) {
  if (!m) { $("metrics").innerHTML = "<p class='hint'>Model not trained yet. Using the heuristic forecaster.</p>"; return; }
  $("metrics").innerHTML = [
    [m.r2, "R² on held-out months"], [m.mae, "MAE (pax/hour)"], [m.event_hours_mae ?? "–", "MAE on event hours"],
    [fmt(m.train_rows), "Training rows"],
  ].map(([v, l]) => `<div class="kpi blue"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("")
    + `<p class="hint" style="grid-column:1/-1">${m.model} · test period ${m.test_period}</p>`;
  const fi = Object.entries(m.feature_importance).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  const mx = Math.max(...fi.map(([, v]) => v));
  $("fi").innerHTML = fi.map(([k, v]) => `<div class="fi-row"><span>${k}</span><div class="fi-bar" style="width:${Math.max(2, (100 * v) / mx)}%"></div><span>${v.toFixed(3)}</span></div>`).join("");
}

init();
