const allActivities = window.GARMIN_TRACKER_DATA || [];

const workouts = allActivities
  .filter((a) => (a.kind || "strength") === "strength")
  .slice()
  .sort((a, b) => parseDate(a.startTimeLocal) - parseDate(b.startTimeLocal));

const runs = allActivities
  .filter((a) => a.kind === "running")
  .slice()
  .sort((a, b) => parseDate(a.startTimeLocal) - parseDate(b.startTimeLocal));

const FOUR_WEEKS_MS = 28 * 24 * 60 * 60 * 1000;
const KG_PER_LB = 1 / 2.2046226218;
const OVERLOAD_REPS = 8;
const OVERLOAD_SESSIONS = 2;

let weightUnit = localStorage.getItem("gt-weight-unit") || "kg";

const els = {
  unitToggle: document.querySelector("#unit-toggle"),
  sHeroNumber: document.querySelector("#s-hero-number"),
  sHeroUnit: document.querySelector("#s-hero-unit"),
  sHeroTrend: document.querySelector("#s-hero-trend"),
  sStatWorkouts: document.querySelector("#s-stat-workouts"),
  sStatPRs: document.querySelector("#s-stat-prs"),
  sStatLast: document.querySelector("#s-stat-last"),
  workoutList: document.querySelector("#workout-list"),
  progressList: document.querySelector("#progress-list"),
  routinePicker: document.querySelector("#routine-picker"),
  routineDetail: document.querySelector("#routine-detail"),
  exercisePicker: document.querySelector("#exercise-picker"),
  exerciseDetail: document.querySelector("#exercise-detail"),
  sEmpty: document.querySelector("#s-empty"),
  rHeroNumber: document.querySelector("#r-hero-number"),
  rHeroTrend: document.querySelector("#r-hero-trend"),
  rStatRuns: document.querySelector("#r-stat-runs"),
  rStatPace: document.querySelector("#r-stat-pace"),
  rStatLast: document.querySelector("#r-stat-last"),
  runList: document.querySelector("#run-list"),
  metricPicker: document.querySelector("#metric-picker"),
  metricDetail: document.querySelector("#metric-detail"),
  rEmpty: document.querySelector("#r-empty"),
};

const RUN_METRICS = {
  Distance: {
    points: (list) => list.map((r) => ({ date: parseDate(r.startTimeLocal), value: r.distanceKm || 0 })),
    formatValue: (v) => round(v, 1).toLocaleString(),
    formatTooltip: (p) => `${formatDateShort(p.date)}: ${round(p.value, 2)} km`,
    lowerIsBetter: false,
    bestLabel: "longest",
  },
  Pace: {
    points: (list) =>
      list.filter((r) => r.avgPaceSecPerKm).map((r) => ({ date: parseDate(r.startTimeLocal), value: r.avgPaceSecPerKm })),
    formatValue: (v) => formatPace(v),
    formatTooltip: (p) => `${formatDateShort(p.date)}: ${formatPace(p.value)}`,
    lowerIsBetter: true,
    bestLabel: "fastest",
  },
  "Heart rate": {
    points: (list) => list.filter((r) => r.avgHR).map((r) => ({ date: parseDate(r.startTimeLocal), value: r.avgHR })),
    formatValue: (v) => `${Math.round(v)} bpm`,
    formatTooltip: (p) => `${formatDateShort(p.date)}: ${Math.round(p.value)} bpm avg`,
    lowerIsBetter: false,
    bestLabel: "highest",
  },
};

init();

function init() {
  wireModeSwitch();
  wireUnitToggle();
  wireTabs();

  if (workouts.length === 0) {
    els.sEmpty.hidden = false;
  } else {
    renderStrengthAll();
  }

  if (runs.length === 0) {
    els.rEmpty.hidden = false;
  } else {
    renderRunningAll();
  }

  showMode("strength");
}

function renderStrengthAll() {
  const exerciseHistory = buildExerciseHistory(workouts);
  const routineHistory = buildRoutineHistory(workouts);
  renderStrengthHero(workouts, exerciseHistory);
  renderWorkouts(workouts);
  renderProgress(exerciseHistory);
  renderRoutinePicker(routineHistory);
  renderExercisePicker(exerciseHistory);
}

function renderRunningAll() {
  renderRunningHero(runs);
  renderRuns(runs);
  renderMetricPicker(runs);
}

// ---------- parsing & formatting ----------

function parseDate(value) {
  return new Date(String(value).replace(" ", "T"));
}

function humanize(rawName) {
  if (!rawName) return "Unclassified";
  return rawName
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatDuration(seconds) {
  const minutes = Math.round((seconds || 0) / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours}h ${rest}m` : `${hours}h`;
}

function convertWeight(kg) {
  if (kg == null) return null;
  return weightUnit === "lb" ? kg / KG_PER_LB : kg;
}

function formatWeight(kg) {
  const value = convertWeight(kg);
  if (!value) return "—";
  return `${round(value, 1).toLocaleString()} ${weightUnit}`;
}

function formatPace(secPerKm) {
  if (!secPerKm) return "—";
  const total = Math.round(secPerKm);
  const min = Math.floor(total / 60);
  const sec = total % 60;
  return `${min}:${String(sec).padStart(2, "0")} /km`;
}

function round(value, decimals) {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

function formatDateShort(date) {
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function relativeDays(date, now) {
  const days = Math.floor((now - date) / (24 * 60 * 60 * 1000));
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  return `${days} days ago`;
}

function sumBy(list, fn) {
  return list.reduce((sum, item) => sum + fn(item), 0);
}

function inWindow(date, now, offsetPeriods) {
  const end = now.getTime() - offsetPeriods * FOUR_WEEKS_MS;
  const start = end - FOUR_WEEKS_MS;
  const t = date.getTime();
  return t >= start && t < end;
}

function trendLabel(recent, prior, hasPrior) {
  if (!hasPrior) return "First 4 weeks tracked";
  if (prior === 0) return recent > 0 ? "No prior sessions to compare" : "No sessions in either period";
  const pct = Math.round(((recent - prior) / prior) * 100);
  if (pct === 0) return "Flat vs previous 4 weeks";
  return `${pct > 0 ? "▲" : "▼"} ${Math.abs(pct)}% vs previous 4 weeks`;
}

// ---------- shared chip helper ----------

function makeChip(label, onClick) {
  const button = document.createElement("button");
  button.className = "chip";
  button.type = "button";
  button.setAttribute("aria-pressed", "false");
  button.innerHTML = label;
  button.addEventListener("click", onClick);
  return button;
}

function setPressed(container, name) {
  for (const { name: chipName, button } of container._chips) {
    button.setAttribute("aria-pressed", String(chipName === name));
  }
}

// ---------- mode switch & unit toggle ----------

function wireModeSwitch() {
  document.querySelectorAll(".mode").forEach((btn) => {
    btn.addEventListener("click", () => showMode(btn.dataset.mode));
  });
}

function showMode(mode) {
  document.querySelectorAll(".mode").forEach((btn) => {
    btn.setAttribute("aria-selected", String(btn.dataset.mode === mode));
  });
  document.querySelectorAll(".mode-panel").forEach((panel) => {
    panel.hidden = panel.dataset.mode !== mode;
  });
  els.unitToggle.hidden = mode !== "strength" || workouts.length === 0;
}

function wireUnitToggle() {
  updateUnitToggleLabel();
  els.unitToggle.addEventListener("click", () => {
    weightUnit = weightUnit === "kg" ? "lb" : "kg";
    localStorage.setItem("gt-weight-unit", weightUnit);
    updateUnitToggleLabel();
    if (workouts.length > 0) renderStrengthAll();
  });
}

function updateUnitToggleLabel() {
  els.unitToggle.textContent = weightUnit === "kg" ? "Switch to lb" : "Switch to kg";
  els.sHeroUnit.textContent = `${weightUnit} lifted, last 4 weeks`;
}

// ---------- tabs (scoped per mode panel) ----------

function wireTabs() {
  document.querySelectorAll(".mode-panel").forEach((panel) => {
    const tabs = panel.querySelectorAll(".tab");
    const views = panel.querySelectorAll(".view");
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((t) => t.setAttribute("aria-selected", String(t === tab)));
        views.forEach((v) => {
          v.hidden = v.dataset.view !== tab.dataset.view;
        });
      });
    });
  });
}

// ---------- strength hero ----------

function renderStrengthHero(workouts, exerciseHistory) {
  const now = new Date();
  const recent = workouts.filter((w) => inWindow(parseDate(w.startTimeLocal), now, 0));
  const prior = workouts.filter((w) => inWindow(parseDate(w.startTimeLocal), now, 1));

  const recentVolume = sumBy(recent, (w) => w.totalVolume || 0);
  const priorVolume = sumBy(prior, (w) => w.totalVolume || 0);

  els.sHeroNumber.textContent = round(convertWeight(recentVolume) || 0, 0).toLocaleString();
  els.sHeroTrend.textContent = trendLabel(recentVolume, priorVolume, prior.length > 0);

  els.sStatWorkouts.textContent = recent.length;
  els.sStatPRs.textContent = countRecentPRs(exerciseHistory, new Date(now.getTime() - FOUR_WEEKS_MS));

  const last = workouts[workouts.length - 1];
  els.sStatLast.textContent = last ? relativeDays(parseDate(last.startTimeLocal), now) : "—";
}

function countRecentPRs(history, cutoff) {
  let count = 0;
  for (const entry of history.values()) {
    const prPoint = entry.points.find((p) => p.value === entry.maxValue);
    if (prPoint && prPoint.date >= cutoff) count += 1;
  }
  return count;
}

// ---------- workouts (log) view ----------

function renderWorkouts(workouts) {
  const items = workouts
    .slice()
    .reverse()
    .map((workout) => workoutRow(workout));
  els.workoutList.replaceChildren(...items);
}

function workoutRow(workout) {
  const date = parseDate(workout.startTimeLocal);
  const sets = workout.sets || [];
  const exerciseNames = [...new Set(sets.map((s) => s.exercise).filter(Boolean))];

  const li = document.createElement("li");
  li.className = "workout-row";

  const summary = document.createElement("button");
  summary.className = "workout-summary";
  summary.innerHTML = `
    <span class="workout-date">
      <span class="day">${date.getDate()}</span>
      <span class="month">${date.toLocaleDateString(undefined, { month: "short" }).toUpperCase()}</span>
    </span>
    <span>
      <p class="workout-title">${workout.activityName || "Workout"}</p>
      <p class="workout-tags">${exerciseNames.map(humanize).join(" · ") || "No classified exercises"}</p>
    </span>
    <span class="workout-metrics">
      <span class="volume">${formatWeight(workout.totalVolume)}</span>
      <span class="duration">${formatDuration(workout.durationSeconds)}</span>
    </span>
  `;

  const detail = document.createElement("div");
  detail.className = "workout-detail";
  detail.innerHTML = `<div>${setTable(sets)}</div>`;

  summary.addEventListener("click", () => {
    const open = li.dataset.open === "true";
    li.dataset.open = String(!open);
  });

  li.append(summary, detail);
  return li;
}

function setTable(sets) {
  const rows = sets
    .filter((s) => s.exercise || s.reps || s.weight)
    .map(
      (s) => `
        <tr>
          <td>${humanize(s.exercise)}</td>
          <td class="num">${s.reps ?? "—"}</td>
          <td class="num">${formatWeight(s.weight)}</td>
        </tr>`
    )
    .join("");
  if (!rows) return "";
  return `
    <table class="set-table">
      <thead><tr><th>Exercise</th><th class="num">Reps</th><th class="num">Weight</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ---------- exercises view ----------

function buildExerciseHistory(workouts) {
  const history = new Map();
  for (const workout of workouts) {
    const date = parseDate(workout.startTimeLocal);
    const bestOfSession = new Map();
    for (const set of workout.sets || []) {
      if (!set.exercise) continue;
      const weight = Number(set.weight || 0);
      const current = bestOfSession.get(set.exercise);
      if (!current || weight > current.value) {
        bestOfSession.set(set.exercise, { value: weight, reps: set.reps });
      }
    }
    for (const [name, best] of bestOfSession) {
      const entry = history.get(name) || { points: [], volume: 0, sets: 0 };
      entry.points.push({ date, value: best.value, reps: best.reps });
      history.set(name, entry);
    }
  }
  for (const workout of workouts) {
    for (const set of workout.sets || []) {
      if (!set.exercise) continue;
      const entry = history.get(set.exercise);
      entry.volume += Number(set.weight || 0) * Number(set.reps || 0);
      entry.sets += 1;
    }
  }
  for (const entry of history.values()) {
    entry.points.sort((a, b) => a.date - b.date);
    entry.maxValue = Math.max(...entry.points.map((p) => p.value));
  }
  return history;
}

function renderExercisePicker(history) {
  const ranked = [...history.entries()].sort((a, b) => b[1].volume - a[1].volume);
  const chips = ranked.map(([name, entry]) => {
    const label = `${entry.maxValue > 0 ? '<span class="pr-dot">●</span> ' : ""}${humanize(name)}`;
    return { name, button: makeChip(label, () => selectExercise(name, history)) };
  });
  els.exercisePicker.replaceChildren(...chips.map((c) => c.button));
  els.exercisePicker._chips = chips;

  if (ranked.length > 0) selectExercise(ranked[0][0], history);
}

function selectExercise(name, history) {
  setPressed(els.exercisePicker, name);
  renderExerciseDetail(name, history.get(name));
}

function renderExerciseDetail(name, entry) {
  const prPoint = entry.points.find((p) => p.value === entry.maxValue);
  const target = progressiveOverloadTarget(entry);
  els.exerciseDetail.innerHTML = `
    <div class="detail-heading">
      <h2>${humanize(name)}</h2>
      <p class="detail-stats">
        <strong>${formatWeight(entry.maxValue)}</strong> PR ·
        <strong>${entry.sets}</strong> sets ·
        <strong>${formatWeight(entry.volume)}</strong> total volume
      </p>
    </div>
    ${targetCard(target)}
    ${lineChart(entry.points, {
      prPoint,
      formatValue: (v) => round(convertWeight(v), 0).toLocaleString(),
      formatTooltip: (p) => `${formatDateShort(p.date)}: ${formatWeight(p.value)} × ${p.reps ?? "?"} reps`,
    })}
  `;
}

function progressiveOverloadTarget(entry) {
  const points = entry.points.filter((p) => p.value > 0 && Number(p.reps) > 0);
  if (points.length < OVERLOAD_SESSIONS) return null;

  const current = points[points.length - 1].value;
  const recentAtCurrent = [];
  for (let i = points.length - 1; i >= 0 && points[i].value === current; i -= 1) {
    recentAtCurrent.push(points[i]);
  }

  const ready = recentAtCurrent.slice(0, OVERLOAD_SESSIONS);
  if (ready.length < OVERLOAD_SESSIONS || ready.some((p) => Number(p.reps) < OVERLOAD_REPS)) {
    return null;
  }

  const displayCurrent = convertWeight(current);
  const displayStep = weightUnit === "lb" ? (displayCurrent >= 100 ? 10 : 5) : displayCurrent >= 45 ? 5 : 2.5;
  const displayNext = round(displayCurrent, 1) + displayStep;
  return {
    current,
    next: weightUnit === "lb" ? displayNext * KG_PER_LB : displayNext,
    reps: Math.min(...ready.map((p) => Number(p.reps))),
    sessions: ready.length,
  };
}

function targetCard(target) {
  if (!target) {
    return `
      <div class="target-card">
        <strong>Target weight</strong>
        <span>Hold current load until ${OVERLOAD_SESSIONS} straight sessions reach ${OVERLOAD_REPS}-${OVERLOAD_REPS + 1} reps.</span>
      </div>`;
  }
  return `
    <div class="target-card ready">
      <strong>Target weight: ${formatWeight(target.next)}</strong>
      <span>Increase from ${formatWeight(target.current)} after ${target.sessions} straight sessions at ${target.reps}+ reps.</span>
    </div>`;
}

// ---------- progress view ----------

function renderProgress(history) {
  const updates = [...history.entries()]
    .map(([name, entry]) => ({ name, target: progressiveOverloadTarget(entry) }))
    .filter((item) => item.target)
    .sort((a, b) => a.name.localeCompare(b.name));

  if (updates.length === 0) {
    els.progressList.innerHTML = `
      <li class="progress-card">
        <strong>No updates ready</strong>
        <span>Keep logging sets until an exercise reaches ${OVERLOAD_REPS}+ reps for ${OVERLOAD_SESSIONS} straight sessions at the same weight.</span>
      </li>`;
    return;
  }

  els.progressList.replaceChildren(...updates.map(progressRow));
}

function progressRow({ name, target }) {
  const li = document.createElement("li");
  li.className = "progress-card ready";
  li.innerHTML = `
    <span>
      <strong>${humanize(name)}</strong>
      <span>${target.sessions} straight sessions at ${target.reps}+ reps</span>
    </span>
    <span class="progress-target">${formatWeight(target.current)} → ${formatWeight(target.next)}</span>
    <code>garmin-tracker progress --unit ${weightUnit}</code>
  `;
  return li;
}

// ---------- routines view ----------

function buildRoutineHistory(workouts) {
  const history = new Map();
  for (const workout of workouts) {
    const name = workout.activityName || "Workout";
    const entry = history.get(name) || { points: [], totalDuration: 0 };
    entry.points.push({
      date: parseDate(workout.startTimeLocal),
      value: workout.totalVolume || 0,
      duration: workout.durationSeconds || 0,
    });
    entry.totalDuration += workout.durationSeconds || 0;
    history.set(name, entry);
  }
  for (const entry of history.values()) {
    entry.points.sort((a, b) => a.date - b.date);
    entry.avgDuration = entry.totalDuration / entry.points.length;
  }
  return history;
}

function renderRoutinePicker(history) {
  const ranked = [...history.entries()].sort((a, b) => b[1].points.length - a[1].points.length);
  const chips = ranked.map(([name, entry]) => ({ name, button: makeChip(name, () => selectRoutine(name, history)) }));
  els.routinePicker.replaceChildren(...chips.map((c) => c.button));
  els.routinePicker._chips = chips;

  if (ranked.length > 0) selectRoutine(ranked[0][0], history);
}

function selectRoutine(name, history) {
  setPressed(els.routinePicker, name);
  renderRoutineDetail(name, history.get(name));
}

function renderRoutineDetail(name, entry) {
  const avgVolume = sumBy(entry.points, (p) => p.value) / entry.points.length;
  const bestVolume = Math.max(...entry.points.map((p) => p.value));
  const prPoint = entry.points.find((p) => p.value === bestVolume);
  els.routineDetail.innerHTML = `
    <div class="detail-heading">
      <h2>${name}</h2>
      <p class="detail-stats">
        <strong>${entry.points.length}</strong> sessions ·
        <strong>${formatWeight(avgVolume)}</strong> avg volume ·
        <strong>${formatDuration(entry.avgDuration)}</strong> avg duration
      </p>
    </div>
    ${lineChart(entry.points, {
      prPoint,
      formatValue: (v) => round(convertWeight(v), 0).toLocaleString(),
      formatTooltip: (p) => `${formatDateShort(p.date)}: ${formatWeight(p.value)} · ${formatDuration(p.duration)}`,
    })}
  `;
}

// ---------- running hero ----------

function renderRunningHero(runs) {
  const now = new Date();
  const recent = runs.filter((r) => inWindow(parseDate(r.startTimeLocal), now, 0));
  const prior = runs.filter((r) => inWindow(parseDate(r.startTimeLocal), now, 1));

  const recentDistance = sumBy(recent, (r) => r.distanceKm || 0);
  const priorDistance = sumBy(prior, (r) => r.distanceKm || 0);

  els.rHeroNumber.textContent = round(recentDistance, 1).toLocaleString();
  els.rHeroTrend.textContent = trendLabel(recentDistance, priorDistance, prior.length > 0);

  els.rStatRuns.textContent = recent.length;
  const bestPace = recent.reduce(
    (best, r) => (r.avgPaceSecPerKm && (!best || r.avgPaceSecPerKm < best) ? r.avgPaceSecPerKm : best),
    null
  );
  els.rStatPace.textContent = formatPace(bestPace);

  const last = runs[runs.length - 1];
  els.rStatLast.textContent = last ? relativeDays(parseDate(last.startTimeLocal), now) : "—";
}

// ---------- runs (log) view ----------

function renderRuns(runs) {
  const items = runs
    .slice()
    .reverse()
    .map((run) => runRow(run));
  els.runList.replaceChildren(...items);
}

function runRow(run) {
  const date = parseDate(run.startTimeLocal);
  const li = document.createElement("li");
  li.className = "workout-row";
  const mapId = `route-${run.activityId}`;
  let mapReady = false;

  const summary = document.createElement("button");
  summary.className = "workout-summary";
  summary.innerHTML = `
    <span class="workout-date">
      <span class="day">${date.getDate()}</span>
      <span class="month">${date.toLocaleDateString(undefined, { month: "short" }).toUpperCase()}</span>
    </span>
    <span>
      <p class="workout-title">${run.activityName || "Run"}</p>
      <p class="workout-tags">${formatPace(run.avgPaceSecPerKm)}${run.avgHR ? ` · ${Math.round(run.avgHR)} bpm avg` : ""}</p>
    </span>
    <span class="workout-metrics">
      <span class="volume">${round(run.distanceKm || 0, 2)} km</span>
      <span class="duration">${formatDuration(run.durationSeconds)}</span>
    </span>
  `;

  const detail = document.createElement("div");
  detail.className = "workout-detail";
  detail.innerHTML = `<div>${runDetailContent(run, mapId)}</div>`;

  summary.addEventListener("click", () => {
    const open = li.dataset.open === "true";
    li.dataset.open = String(!open);
    // Init on first expand only: no point fetching map tiles for rows never opened.
    if (!open && !mapReady && run.route && run.route.length > 1) {
      initRouteMap(mapId, run.route);
      mapReady = true;
    }
  });

  li.append(summary, detail);
  return li;
}

function runDetailContent(run, mapId) {
  const stats = `
    <p class="run-stats">
      <span><strong>${formatPace(run.avgPaceSecPerKm)}</strong> pace</span>
      <span><strong>${run.avgHR ? Math.round(run.avgHR) : "—"}</strong> avg HR</span>
      <span><strong>${run.maxHR ? Math.round(run.maxHR) : "—"}</strong> max HR</span>
      <span><strong>${run.elevationGainM ? Math.round(run.elevationGainM) : "—"}</strong> m gain</span>
      <span><strong>${run.cadence ? Math.round(run.cadence) : "—"}</strong> spm</span>
      <span><strong>${run.calories ? Math.round(run.calories) : "—"}</strong> kcal</span>
    </p>`;
  const map = run.route && run.route.length > 1 ? `<div class="route-map" id="${mapId}"></div>` : "";
  return stats + map;
}

function initRouteMap(containerId, route) {
  const map = L.map(containerId);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);
  const line = L.polyline(
    route.map((p) => [p.lat, p.lon]),
    { color: "#6e9ab0", weight: 3 }
  ).addTo(map);
  map.fitBounds(line.getBounds(), { padding: [12, 12] });
}

// ---------- running trends view ----------

function renderMetricPicker(runs) {
  const names = Object.keys(RUN_METRICS);
  const chips = names.map((name) => ({ name, button: makeChip(name, () => selectMetric(name, runs)) }));
  els.metricPicker.replaceChildren(...chips.map((c) => c.button));
  els.metricPicker._chips = chips;
  selectMetric(names[0], runs);
}

function selectMetric(name, runs) {
  setPressed(els.metricPicker, name);
  const config = RUN_METRICS[name];
  const points = config.points(runs).sort((a, b) => a.date - b.date);

  if (points.length === 0) {
    els.metricDetail.innerHTML = `<p class="empty">No ${name.toLowerCase()} data yet.</p>`;
    return;
  }

  const values = points.map((p) => p.value);
  const bestValue = config.lowerIsBetter ? Math.min(...values) : Math.max(...values);
  const prPoint = points.find((p) => p.value === bestValue);

  els.metricDetail.innerHTML = `
    <div class="detail-heading">
      <h2>${name}</h2>
      <p class="detail-stats">
        <strong>${config.formatValue(bestValue)}</strong> ${config.bestLabel} ·
        <strong>${points.length}</strong> runs
      </p>
    </div>
    ${lineChart(points, { prPoint, formatValue: config.formatValue, formatTooltip: config.formatTooltip })}
  `;
}

// ---------- shared chart (date-scaled x-axis) ----------

function lineChart(points, options = {}) {
  if (points.length === 0) return "";
  const { prPoint = null, formatValue = (v) => String(Math.round(v)), formatTooltip = null } = options;

  const width = 640;
  const height = 240;
  const padL = 46;
  const padR = 16;
  const padT = 20;
  const padB = 32;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const maxValue = Math.max(...points.map((p) => p.value), 1);
  const niceMax = Math.ceil((maxValue * 1.15) / 5) * 5 || 1;

  const times = points.map((p) => p.date.getTime());
  const minT = Math.min(...times);
  const maxT = Math.max(...times);
  const span = maxT - minT || 1;

  const xFor = (p) => padL + (points.length === 1 ? plotW / 2 : ((p.date.getTime() - minT) / span) * plotW);
  const yFor = (v) => padT + plotH - (v / niceMax) * plotH;

  const gridLines = [0, 0.25, 0.5, 0.75, 1]
    .map((t) => {
      const y = padT + plotH - t * plotH;
      return `<line x1="${padL}" y1="${y.toFixed(1)}" x2="${width - padR}" y2="${y.toFixed(1)}" class="grid" />
        <text x="${padL - 8}" y="${(y + 4).toFixed(1)}" class="axis-label" text-anchor="end">${formatValue(niceMax * t)}</text>`;
    })
    .join("");

  const line =
    points.length > 1
      ? `<polyline points="${points.map((p) => `${xFor(p).toFixed(1)},${yFor(p.value).toFixed(1)}`).join(" ")}" class="chart-line" fill="none" />`
      : "";

  let lastLabelX = -Infinity;
  const dots = points
    .map((p, i) => {
      const x = xFor(p);
      const y = yFor(p.value);
      const isPR = prPoint && p === prPoint;
      const tooltip = formatTooltip ? formatTooltip(p) : `${formatDateShort(p.date)}: ${formatValue(p.value)}`;
      const showLabel = i === 0 || i === points.length - 1 || x - lastLabelX > 60;
      if (showLabel) lastLabelX = x;
      return `
        <g class="dot${isPR ? " dot-pr" : ""}">
          <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${isPR ? 6 : 4}"><title>${tooltip}</title></circle>
          ${isPR ? `<text x="${x.toFixed(1)}" y="${(y - 14).toFixed(1)}" class="pr-label" text-anchor="middle">PR</text>` : ""}
        </g>
        ${showLabel ? `<text x="${x.toFixed(1)}" y="${height - 8}" class="axis-label" text-anchor="middle">${formatDateShort(p.date)}</text>` : ""}
      `;
    })
    .join("");

  return `
    <svg viewBox="0 0 ${width} ${height}" class="chart" role="img" aria-label="Trend over time">
      ${gridLines}
      ${line}
      ${dots}
    </svg>`;
}
