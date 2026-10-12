"use strict";
/* Garmin Health dashboard. Pages: today, sleep, activities, trends.
   Detail screens slide in over them: #m/<metric>[/<date>] and #a/<activity id>. */

// ---- strings ----------------------------------------------------------------
const STR = {
  he: {
    today: "היום", sleep: "שינה", acts: "פעילויות", trends: "מגמות", back: "חזרה", all: "הכל",
    yourMetrics: "המדדים שלך", recentActs: "פעילויות אחרונות", recovery: "התאוששות",
    good: ["התאוששת היטב", "הגוף מוכן ליום תובעני."], fair: ["התאוששות בינונית", "יום מתון יתאים לך היום."],
    low: ["הגוף עייף", "כדאי להוריד עומס היום."], unknown: ["אין עדיין נתונים", "סנכרן את השעון כדי לראות את ההתאוששות."],
    basis: d => `מבוסס על הלילה של ${d}`,
    hrvLow: "HRV מתחת לטווח שלך", hrvHigh: "HRV מעל הטווח", hrvOk: "HRV בטווח שלך", shortSleep: "שינה קצרה",
    greatSleep: "שינה מצוינת", rhrHigh: "דופק מנוחה גבוה מהרגיל", rhrLow: "דופק מנוחה נמוך", bbLow: "Body Battery נמוך",
    bbHigh: "סוללה מלאה", rampUp: "עומס אימונים עולה מהר",
    m: {
      sleep: "שינה", hrv: "HRV", rhr: "דופק", bb: "Body Battery", spo2: "רוויית חמצן", stress: "סטרס",
      steps: "צעדים", readiness: "מוכנות", fitness: "גיל כושר", vo2: "VO2 max", resp: "נשימה",
    },
    ex: {
      hrv: "השונות בין פעימות הלב בזמן השינה. ערך גבוה ויציב בתוך הטווח האישי שלך מעיד על מערכת עצבים רגועה והתאוששות טובה. ירידה מתחת לטווח יכולה להעיד על עייפות, מחלה מתקרבת, אלכוהול או סטרס.",
      rhr: "הדופק לאורך היום והלילה. דופק המנוחה נמדד בשעות השקטות. עלייה של כמה פעימות מעל הממוצע שלך היא סימן מוקדם לעומס או מחלה.",
      bb: "מדד האנרגיה של Garmin, מ-0 עד 100. נטען בשינה ובמנוחה, ומתרוקן בפעילות ובסטרס.",
      spo2: "אחוז החמצן בדם במהלך הלילה. רוב האנשים נמצאים בין 95% ל-100%. ירידות קצרות בלילה הן נורמליות; ירידות חוזרות ועמוקות שווה לבדוק.",
      stress: "רמת הסטרס של Garmin, מחושבת מ-HRV. 0-25 מנוחה, 26-50 נמוך, 51-75 בינוני, 76-100 גבוה.",
      steps: "צעדים לאורך היום, ברבעי שעה.",
      readiness: "ציון המוכנות לאימון של Garmin, משקלל את כל הגורמים שלמטה.",
      fitness: "הגיל שהכושר שלך מתאים לו לפי Garmin, ומה הכי ישפר אותו.",
      vo2: "צריכת החמצן המקסימלית, המדד המרכזי לכושר אירובי.",
      resp: "קצב הנשימה בדקה במהלך הלילה. אצל רוב המבוגרים 12-20.",
    },
    vo2Est: "ל-Garmin אין עדיין ערך, כי הוא מחושב רק מריצה או רכיבה עם GPS. המספר כאן הוא הערכה גסה לפי דופק המנוחה והגיל (נוסחת Uth), לא מדידה.",
    vo2Garmin: "הערך של Garmin.", estimate: "הערכה",
    min: "מינימום", avg: "ממוצע", max: "מקסימום", lowest: "הנמוך", latest: "אחרון", total: "סה״כ", goal: "יעד",
    night: "בלילה", dayTime: "במהלך היום", noData: "אין נתונים ליום הזה.", noIntraday: "הנתונים הדקה-אחר-דקה של היום הזה עוד לא הורדו. הם יתמלאו בסנכרונים הקרובים.",
    deep: "עמוקה", light: "קלה", rem: "REM", awake: "ער", score: "ציון", need: n => `צורך השינה שלך: ${n}`,
    asleep: "שינה", bedtime: "הירדמות", wake: "התעוררות", restless: "תזוזות", vitalsNight: "בלילה", resp: "נשימה",
    hrNight: "דופק בלילה", hrvNight: "HRV בלילה", spo2Night: "חמצן בלילה", respNight: "נשימה בלילה", bbNight: "סטרס ו-Body Battery בלילה",
    factors: "מה משפיע", trend: "מגמה", components: "מה ישפר את גיל הכושר",
    fa: { vigorousDaysAvg: "ימים עצימים בשבוע", vigorousMinutesAvg: "דקות עצימות בשבוע", bmi: "BMI", rhr: "דופק מנוחה" },
    actual: a => `גיל בפועל ${a}`, younger: d => `צעיר ב-${d} שנים`, older: d => `מבוגר ב-${d} שנים`, achievable: a => `אפשר להגיע ל-${a}`,
    target: t => `יעד ${t}`, potential: a => `ישפר לגיל ${a}`,
    rf: { sleepScore: "ציון שינה", recoveryTime: "זמן התאוששות", acwr: "עומס אימונים", stressHistory: "סטרס בימים האחרונים", hrv: "HRV", sleepHistory: "שינה בימים האחרונים" },
    fb: { VERY_GOOD: "מצוין", GOOD: "טוב", MODERATE: "בינוני", POOR: "חלש", VERY_POOR: "חלש מאוד" },
    levels: { POOR: "חלשה", LOW: "נמוכה", MODERATE: "בינונית", HIGH: "גבוהה", PRIME: "מעולה" },
    hrvStatus: { BALANCED: "מאוזן", UNBALANCED: "לא מאוזן", LOW: "נמוך", POOR: "חלש" },
    stressLv: s => s <= 25 ? "מנוחה" : s <= 50 ? "נמוך" : s <= 75 ? "בינוני" : "גבוה",
    sleepFb: k => /^POSITIVE/.test(k || "") ? "שינה משקמת" : /^NEGATIVE/.test(k || "") ? "שינה פחות משקמת" : "",
    duration: "משך", distance: "מרחק", pace: "קצב", speed: "מהירות", avgHr: "דופק ממוצע", maxHr: "דופק מקסימלי", calories: "קלוריות",
    load: "עומס", aerobic: "אפקט אירובי", anaerobic: "אפקט אנאירובי", swolf: "SWOLF", strokes: "תנועות", temp: "טמפרטורה",
    maxDepth: "עומק מקסימלי", avgDepth: "עומק ממוצע", dives: "צלילות", bottom: "זמן בעומק", surface: "זמן מנוחה", bbDiff: "Body Battery",
    elev: "עלייה", moving: "זמן תנועה", intensity: "דקות עצימות", route: "מסלול", hrZones: "אזורי דופק", laps: "הקפות",
    hrChart: "דופק", speedChart: "קצב", depthChart: "עומק", tempChart: "טמפרטורת מים", cadenceChart: "קצב תנועה",
    zonesNote: m => `לפי דופק מקסימלי ${m}`, lap: "#", km: "ק״מ", m100: "/100מ׳", perKm: "/ק״מ", kmh: "קמ״ש",
    noActs: "אין פעילויות.", thisWeek: "השבוע", weekOf: d => `שבוע של ${d}`,
    types: {
      running: "ריצה", trail_running: "ריצת שטח", treadmill_running: "ריצה על הליכון", walking: "הליכה", hiking: "טיול רגלי",
      cycling: "רכיבה", road_biking: "רכיבת כביש", mountain_biking: "רכיבת שטח", indoor_cycling: "אופני כושר",
      lap_swimming: "שחייה בבריכה", open_water_swimming: "שחייה במים פתוחים", strength_training: "אימון כוח",
      yoga: "יוגה", cardio: "קרדיו", hiit: "HIIT", apnea_diving: "צלילה חופשית", free_diving: "צלילה חופשית",
      snorkeling: "שנורקלינג", breathwork: "נשימות",
    },
    watchAgo: r => `השעון העלה ${r}`, checked: r => `נבדק ${r}`, noSync: "עדיין אין סנכרון מהשעון",
    ago: m => m < 1 ? "עכשיו" : m < 60 ? `לפני ${m} דק׳` : m < 2880 ? `לפני ${Math.floor(m / 60)} ש׳` : `לפני ${Math.floor(m / 1440)} ימים`,
    stale: h => `השעון לא העלה נתונים ${h} שעות. סנכרן אותו כדי לקבל נתונים עדכניים.`,
    lastRun: s => `סנכרון אחרון: ${({ ok: "תקין", error: "שגיאה", rate_limited: "נחסם זמנית", login_needed: "נדרשת התחברות", skipped: "דולג", unchanged: "אין חדש מהשעון" })[s] || s}`,
    syncDone: "עודכן", syncRunning: "סנכרון כבר רץ", syncRecent: m => `נבדק הרגע. נסה שוב בעוד ${m} דק׳`,
    syncBlocked: "הסנכרון מושהה כדי להגן על החשבון",
    noNew: t => `אין נתונים חדשים: השעון לא העלה מאז ${t}. סנכרן את השעון ולחץ שוב.`,
    settings: "הגדרות", language: "שפה", device: "שעון", syncNow: "סנכרן עכשיו",
    days: ["א׳", "ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳"],
    longDays: ["יום ראשון", "יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "שבת"],
    hours: "ש׳", bpm: "פעימות", perMin: "לדקה", ms: "ms",
    t_sleepStages: "שלבי שינה", t_hrv: "HRV", t_rhr: "דופק במנוחה", t_bb: "Body Battery", t_stress: "סטרס", t_steps: "צעדים",
    t_spo2: "רוויית חמצן בלילה", t_load: "עומס אימונים", t_ready: "מוכנות", t_score: "ציון שינה",
    lastNight: "לילה", weekly: "ממוצע 7 ימים", range: "טווח", high: "גבוה", atWake: "בהתעוררות", acute: "אקוטי", chronic: "כרוני", daily: "פעילות",
  },
  en: {
    today: "Today", sleep: "Sleep", acts: "Activities", trends: "Trends", back: "Back", all: "All",
    yourMetrics: "Your metrics", recentActs: "Recent activities", recovery: "Recovery",
    good: ["Well recovered", "Your body is ready for a demanding day."], fair: ["Moderately recovered", "A moderate day suits you best."],
    low: ["Your body is tired", "Consider going easy today."], unknown: ["No data yet", "Sync the watch to see today's recovery."],
    basis: d => `Based on the night of ${d}`,
    hrvLow: "HRV below your range", hrvHigh: "HRV above range", hrvOk: "HRV in your range", shortSleep: "Short sleep",
    greatSleep: "Great sleep", rhrHigh: "Resting HR is up", rhrLow: "Resting HR is low", bbLow: "Low Body Battery",
    bbHigh: "Full battery", rampUp: "Load rising fast",
    m: {
      sleep: "Sleep", hrv: "HRV", rhr: "Heart rate", bb: "Body Battery", spo2: "Blood oxygen", stress: "Stress",
      steps: "Steps", readiness: "Readiness", fitness: "Fitness age", vo2: "VO2 max", resp: "Breathing",
    },
    ex: {
      hrv: "Variation between heartbeats during sleep. High and steady within your personal range means a calm nervous system and good recovery. Dropping below it can point to fatigue, illness, alcohol or stress.",
      rhr: "Heart rate through the day and night. A few beats above your average resting HR is an early sign of strain or illness.",
      bb: "Garmin's energy score from 0 to 100. Charges during sleep and rest, drains with activity and stress.",
      spo2: "Blood oxygen during the night. Most people sit between 95% and 100%. Brief dips at night are normal; repeated deep dips are worth checking.",
      stress: "Garmin's stress level, from HRV. 0-25 rest, 26-50 low, 51-75 medium, 76-100 high.",
      steps: "Steps through the day, per 15 minutes.",
      readiness: "Garmin's training readiness, weighing the factors below.",
      fitness: "The age your fitness matches according to Garmin, and what would improve it most.",
      vo2: "Maximal oxygen uptake, the main measure of aerobic fitness.",
      resp: "Breaths per minute during the night. Most adults are at 12-20.",
    },
    vo2Est: "Garmin has no value yet; it needs GPS runs or rides. This number is a rough estimate from resting HR and age (Uth formula), not a measurement.",
    vo2Garmin: "Garmin's value.", estimate: "estimate",
    min: "Min", avg: "Average", max: "Max", lowest: "Lowest", latest: "Latest", total: "Total", goal: "Goal",
    night: "Night", dayTime: "Day", noData: "No data for this day.", noIntraday: "Minute-level data for this day isn't downloaded yet. It fills in over the next syncs.",
    deep: "Deep", light: "Light", rem: "REM", awake: "Awake", score: "Score", need: n => `Your sleep need: ${n}`,
    asleep: "Asleep", bedtime: "Bedtime", wake: "Wake", restless: "Restless", vitalsNight: "Overnight", resp: "Breathing",
    hrNight: "Heart rate overnight", hrvNight: "HRV overnight", spo2Night: "Blood oxygen overnight", respNight: "Breathing overnight", bbNight: "Stress and Body Battery overnight",
    factors: "What drives it", trend: "Trend", components: "What would improve your fitness age",
    fa: { vigorousDaysAvg: "Vigorous days per week", vigorousMinutesAvg: "Vigorous minutes per week", bmi: "BMI", rhr: "Resting HR" },
    actual: a => `Actual age ${a}`, younger: d => `${d} years younger`, older: d => `${d} years older`, achievable: a => `Achievable ${a}`,
    target: t => `target ${t}`, potential: a => `would bring you to ${a}`,
    rf: { sleepScore: "Sleep score", recoveryTime: "Recovery time", acwr: "Training load", stressHistory: "Recent stress", hrv: "HRV", sleepHistory: "Recent sleep" },
    fb: { VERY_GOOD: "Very good", GOOD: "Good", MODERATE: "Moderate", POOR: "Poor", VERY_POOR: "Very poor" },
    levels: {}, hrvStatus: {},
    stressLv: s => s <= 25 ? "rest" : s <= 50 ? "low" : s <= 75 ? "medium" : "high",
    sleepFb: k => /^POSITIVE/.test(k || "") ? "Restorative sleep" : /^NEGATIVE/.test(k || "") ? "Less restorative sleep" : "",
    duration: "Duration", distance: "Distance", pace: "Pace", speed: "Speed", avgHr: "Avg HR", maxHr: "Max HR", calories: "Calories",
    load: "Load", aerobic: "Aerobic effect", anaerobic: "Anaerobic effect", swolf: "SWOLF", strokes: "Strokes", temp: "Temperature",
    maxDepth: "Max depth", avgDepth: "Avg depth", dives: "Dives", bottom: "Bottom time", surface: "Surface interval", bbDiff: "Body Battery",
    elev: "Ascent", moving: "Moving time", intensity: "Intensity minutes", route: "Route", hrZones: "Heart rate zones", laps: "Laps",
    hrChart: "Heart rate", speedChart: "Pace", depthChart: "Depth", tempChart: "Water temperature", cadenceChart: "Cadence",
    zonesNote: m => `Using max HR ${m}`, lap: "#", km: "km", m100: "/100m", perKm: "/km", kmh: "km/h",
    noActs: "No activities.", thisWeek: "This week", weekOf: d => `Week of ${d}`,
    types: {},
    watchAgo: r => `Watch uploaded ${r}`, checked: r => `checked ${r}`, noSync: "No watch sync yet",
    ago: m => m < 1 ? "just now" : m < 60 ? `${m} min ago` : m < 2880 ? `${Math.floor(m / 60)} h ago` : `${Math.floor(m / 1440)} days ago`,
    stale: h => `The watch hasn't uploaded in ${h} hours. Sync it to get fresh data.`,
    lastRun: s => `Last sync: ${s.replace(/_/g, " ")}`,
    syncDone: "Updated", syncRunning: "A sync is already running", syncRecent: m => `Checked a moment ago. Try again in ${m} min`,
    syncBlocked: "Sync paused to protect the account",
    noNew: t => `Nothing new: the watch hasn't uploaded since ${t}. Sync the watch, then tap again.`,
    settings: "Settings", language: "Language", device: "Watch", syncNow: "Sync now",
    days: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    longDays: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    hours: "h", bpm: "bpm", perMin: "/min", ms: "ms",
    t_sleepStages: "Sleep stages", t_hrv: "HRV", t_rhr: "Resting heart rate", t_bb: "Body Battery", t_stress: "Stress", t_steps: "Steps",
    t_spo2: "Blood oxygen overnight", t_load: "Training load", t_ready: "Readiness", t_score: "Sleep score",
    lastNight: "Night", weekly: "7-day avg", range: "Range", high: "High", atWake: "At wake", acute: "Acute", chronic: "Chronic", daily: "Activity",
  },
};
const T = STR[LANG];
document.querySelectorAll("[data-t]").forEach(el => { if (typeof T[el.dataset.t] === "string") el.textContent = T[el.dataset.t]; });

// ---- helpers ------------------------------------------------------------------
const $ = id => document.getElementById(id);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const pad = n => String(n).padStart(2, "0");
const isoDay = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const todayIso = () => isoDay(new Date());
const addDays = (ds, n) => { const d = new Date(ds + "T12:00"); d.setDate(d.getDate() + n); return isoDay(d); };
const dm = ds => `${+ds.slice(8, 10)}.${+ds.slice(5, 7)}`;
const dayLabel = ds => ds === todayIso() ? T.today : `${T.longDays[new Date(ds + "T12:00").getDay()]} ${dm(ds)}`;
const hhmm = ms => { const d = new Date(ms); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
const hm = s => s == null ? "–" : `${Math.floor(s / 3600)}:${pad(Math.floor(s % 3600 / 60))}`;
const mss = s => s == null ? "–" : s >= 3600 ? hm(s) : `${Math.floor(s / 60)}:${pad(Math.round(s % 60))}`;
const n0 = x => x == null ? "–" : Math.round(x).toLocaleString();
const n1 = x => x == null ? "–" : (Math.round(x * 10) / 10).toLocaleString();
const minsSince = iso => Math.max(0, Math.floor((Date.now() - new Date(iso)) / 60000));
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const raf2 = fn => requestAnimationFrame(() => requestAnimationFrame(fn));
const vals = series => (series || []).map(p => p[1]).filter(v => v != null);
const statsOf = series => { const v = vals(series); return v.length ? { min: Math.min(...v), max: Math.max(...v), avg: v.reduce((a, b) => a + b, 0) / v.length, last: v[v.length - 1] } : null; };

const cache = new Map();
async function get(url, fresh = false) {
  if (!fresh && cache.has(url)) return cache.get(url);
  const p = fetch(url).then(r => r.json());
  cache.set(url, p);
  p.catch(() => cache.delete(url));
  return p;
}

function animateIn(root) {
  raf2(() => {
    root.querySelectorAll("[data-w]").forEach(el => el.style.width = el.dataset.w + "%");
    root.querySelectorAll(".arc[data-off]").forEach(el => el.style.strokeDashoffset = el.dataset.off);
  });
}
function countUp(el, target, fmt = v => Math.round(v)) {
  if (target == null) { el.textContent = "–"; return; }
  if (still) { el.textContent = fmt(target); return; }
  const t0 = performance.now();
  const step = t => { const p = Math.min(1, (t - t0) / 900), e = 1 - Math.pow(1 - p, 3); el.textContent = fmt(target * e); if (p < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

let toastTimer;
function toast(msg) { const el = $("toast"); el.textContent = msg; el.classList.add("on"); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove("on"), 3400); }

// ---- icons & metric meta --------------------------------------------------------
const ICON = {
  sleep: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  hrv: '<path d="M3 12h3l2-5 3 10 3-8 2 3h5"/>',
  rhr: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
  bb: '<rect x="3" y="7" width="16" height="10" rx="2.5"/><path d="M22 11v2M7 10v4M11 10v4"/>',
  spo2: '<path d="M12 3s6 6.6 6 11a6 6 0 0 1-12 0c0-4.4 6-11 6-11z"/>',
  stress: '<path d="M4 16c2-6 4-6 6 0s4 6 6 0 4-6 4-6"/>',
  steps: '<path d="M8 3c2 0 3 2 3 5s-1 5-3 5-3-1-3-4 1-6 3-6zM16 9c2 0 3 2 3 5s-1 5-3 5-3-1-3-4 1-6 3-6z"/>',
  readiness: '<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>',
  fitness: '<circle cx="12" cy="8" r="4"/><path d="M5 21c1-4 4-6 7-6s6 2 7 6"/>',
  vo2: '<path d="M4 14a8 8 0 0 1 16 0M12 14l4-4"/><circle cx="12" cy="14" r="1.5"/>',
  resp: '<path d="M12 4v8M12 12c-2 0-6 1-6 6 0 2 2 2 3 1l3-3M12 12c2 0 6 1 6 6 0 2-2 2-3 1l-3-3"/>',
  swim: '<path d="M2 16c2 0 2-1.5 4-1.5S8 16 10 16s2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5M2 20c2 0 2-1.5 4-1.5S8 20 10 20s2-1.5 4-1.5 2 1.5 4 1.5 2-1.5 4-1.5"/><circle cx="16" cy="6" r="2"/><path d="M5 12l5-4 3 3"/>',
  bike: '<circle cx="6" cy="16" r="4"/><circle cx="18" cy="16" r="4"/><path d="M6 16l4-7h5l3 7M10 9l3 7"/>',
  strength: '<path d="M6 7v10M18 7v10M3 10v4M21 10v4M6 12h12"/>',
  walk: '<circle cx="13" cy="4" r="2"/><path d="M9 21l3-7 3 3v4M12 14l-1-5 4 2 2 3M11 9l-3 3"/>',
  dive: '<path d="M12 3v14M7 12l5 5 5-5M4 21h16"/>',
  other: '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
};
const svgI = (k, cls = "i") => `<svg class="${cls}" viewBox="0 0 24 24">${ICON[k] || ICON.other}</svg>`;
const CHEV = '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>';
const actKind = t => /div|apnea|snorkel/.test(t) ? "dive" : /swim/.test(t) ? "swim" : /bik|cycl/.test(t) ? "bike" : /strength|hiit/.test(t) ? "strength" : /run|walk|hik/.test(t) ? "walk" : "other";
const actColor = t => ({ dive: "--spo2", swim: "--bb", bike: "--stress", strength: "--rhr", walk: "--steps", other: "--fit" })[actKind(t)];
const actName = a => (T.types[a.type] || a.name || (a.type || "").replace(/_/g, " "));

// ---- tiny SVG visualisations ----------------------------------------------------
function ringSvg(pct, color, width) {
  const r = 50 - width / 2, v = pct == null ? 0 : Math.max(0, Math.min(100, pct));
  return `<svg viewBox="0 0 100 100"><circle class="track" cx="50" cy="50" r="${r}" stroke-width="${width}"/>
    <circle class="arc" cx="50" cy="50" r="${r}" stroke-width="${width}" pathLength="100" stroke="${color}" data-off="${100 - v}"
      style="filter: drop-shadow(0 0 ${width * .6}px ${color}55)"/></svg>`;
}
// values: numbers or nulls, equally spaced. Draws a smooth line, optional area and band.
function spark(values, color, { area = true, band = null, h = 46, dot = true, min = null, max = null } = {}) {
  const pts = values.map((v, i) => [i, v]).filter(p => p[1] != null);
  if (pts.length < 2) return "";
  const W = 200, lo = min ?? Math.min(...pts.map(p => p[1]), ...(band || [])), hi = max ?? Math.max(...pts.map(p => p[1]), ...(band || []));
  const span = hi - lo || 1, n = values.length - 1 || 1;
  const X = i => (i / n) * W, Y = v => h - 3 - ((v - lo) / span) * (h - 8);
  let d = `M${X(pts[0][0])},${Y(pts[0][1])}`;
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = [X(pts[i - 1][0]), Y(pts[i - 1][1])], [x1, y1] = [X(pts[i][0]), Y(pts[i][1])], cx = (x0 + x1) / 2;
    d += ` C${cx},${y0} ${cx},${y1} ${x1},${y1}`;
  }
  const id = "g" + Math.random().toString(36).slice(2, 8), last = pts[pts.length - 1];
  return `<svg viewBox="0 0 ${W} ${h}" preserveAspectRatio="none" direction="ltr">
    <defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".35"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
    ${band ? `<rect x="0" width="${W}" y="${Y(band[1])}" height="${Math.max(1, Y(band[0]) - Y(band[1]))}" fill="${color}" opacity=".12" rx="3"/>` : ""}
    ${area ? `<path d="${d} L${X(last[0])},${h} L${X(pts[0][0])},${h} Z" fill="url(#${id})"/>` : ""}
    <path d="${d}" fill="none" stroke="${color}" stroke-width="2.2" vector-effect="non-scaling-stroke" stroke-linecap="round"/>
    ${dot ? `<circle cx="${X(last[0])}" cy="${Y(last[1])}" r="3.2" fill="${color}" vector-effect="non-scaling-stroke"/>` : ""}</svg>`;
}
function bars(values, colorFn, h = 46) {
  const W = 200, n = values.length, max = Math.max(1, ...values.map(v => v || 0)), bw = W / n;
  return `<svg viewBox="0 0 ${W} ${h}" preserveAspectRatio="none" direction="ltr">${values.map((v, i) => v ? `<rect x="${i * bw + bw * .15}" width="${bw * .7}" y="${h - (v / max) * h}" height="${(v / max) * h}" rx="${Math.min(2, bw * .3)}" fill="${colorFn(v, i)}"/>` : "").join("")}</svg>`;
}
const STAGE_ROW = { awake: 0, rem: 1, light: 2, deep: 3 };
function hypnogram(sleep, { h = 170, labels = true } = {}) {
  if (!sleep || !sleep.levels.length) return "";
  const W = 1000, top = labels ? 4 : 0, bottom = labels ? 22 : 0, rowH = (h - top - bottom) / 4;
  const t0 = sleep.start || sleep.levels[0].s, t1 = sleep.end || sleep.levels[sleep.levels.length - 1].e, X = t => ((t - t0) / (t1 - t0)) * W;
  let out = "", prev = null;
  for (const lv of sleep.levels) {
    const row = STAGE_ROW[lv.stage], y = top + row * rowH, x = X(lv.s), w = Math.max(2, X(lv.e) - x), c = css(`--${lv.stage}`);
    if (prev) { const py = top + STAGE_ROW[prev.stage] * rowH; out += `<line x1="${x}" x2="${x}" y1="${Math.min(py, y) + rowH / 2}" y2="${Math.max(py, y) + rowH / 2}" stroke="rgba(255,255,255,.18)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`; }
    out += `<rect x="${x}" y="${y + rowH * .12}" width="${w}" height="${rowH * .76}" rx="${Math.min(rowH * .3, 6)}" fill="${c}"/>`;
    prev = lv;
  }
  // Hour labels as HTML: text inside a stretched SVG would be distorted.
  let ticks = "";
  if (labels) {
    const first = new Date(t0); first.setMinutes(0, 0, 0);
    for (let t = first.getTime() + 3600e3; t < t1; t += 3600e3) {
      if (new Date(t).getHours() % 2) continue;
      ticks += `<span style="left:${(X(t) / W) * 100}%">${hhmm(t)}</span>`;
    }
  }
  return `<div class="hypnowrap"><svg class="hypno" viewBox="0 0 ${W} ${h - bottom}" preserveAspectRatio="none" direction="ltr" style="height:${h - bottom}px">${out}</svg>${labels ? `<div class="hticks">${ticks}</div>` : ""}</div>`;
}
function routeSvg(route) {
  if (!route || route.length < 2) return "";
  const lat0 = route.reduce((a, p) => a + p[0], 0) / route.length, k = Math.cos(lat0 * Math.PI / 180);
  const xs = route.map(p => p[1] * k), ys = route.map(p => -p[0]);
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const W = 1000, H = 520, padd = 50, s = Math.min((W - 2 * padd) / (maxX - minX || 1), (H - 2 * padd) / (maxY - minY || 1));
  const ox = (W - (maxX - minX) * s) / 2, oy = (H - (maxY - minY) * s) / 2;
  const P = i => [(xs[i] - minX) * s + ox, (ys[i] - minY) * s + oy];
  const d = route.map((_, i) => (i ? "L" : "M") + P(i).map(v => v.toFixed(1)).join(",")).join("");
  const [sx, sy] = P(0), [ex, ey] = P(route.length - 1);
  return `<svg class="route" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" direction="ltr">
    <defs><linearGradient id="rg" x1="0" x2="1"><stop offset="0" stop-color="${css("--bb")}"/><stop offset="1" stop-color="${css("--good")}"/></linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="6"/></filter></defs>
    <path d="${d}" fill="none" stroke="url(#rg)" stroke-width="10" opacity=".35" filter="url(#glow)" stroke-linejoin="round"/>
    <path d="${d}" fill="none" stroke="url(#rg)" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${sx}" cy="${sy}" r="11" fill="${css("--good")}" stroke="#000" stroke-width="4"/>
    <circle cx="${ex}" cy="${ey}" r="11" fill="${css("--low")}" stroke="#000" stroke-width="4"/></svg>`;
}

// ---- charts ----------------------------------------------------------------------
Chart.defaults.color = "#8e8e93";
Chart.defaults.borderColor = "rgba(255,255,255,.06)";
Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
Chart.defaults.font.size = 11;
Chart.defaults.maintainAspectRatio = false;
Chart.defaults.spanGaps = true;
Chart.defaults.animation.duration = still ? 0 : 700;
Chart.defaults.interaction = { mode: "index", intersect: false };
Chart.defaults.plugins.legend.labels.boxWidth = 8;
Chart.defaults.plugins.legend.labels.boxHeight = 8;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Object.assign(Chart.defaults.plugins.tooltip, {
  backgroundColor: "rgba(44,44,50,.92)", borderColor: "rgba(255,255,255,.12)", borderWidth: .5,
  padding: 10, cornerRadius: 12, titleFont: { weight: "600" }, displayColors: true, boxPadding: 4,
});
Chart.defaults.scale.ticks.maxRotation = 0;
Chart.defaults.scale.ticks.autoSkipPadding = 16;

const charts = { page: [], sheet: [] };
function killCharts(scope) { charts[scope].forEach(c => c.destroy()); charts[scope] = []; }
function mk(scope, el, cfg) { if (!el) return null; const c = new Chart(el, cfg); charts[scope].push(c); return c; }
function grad(color, a = .35) {
  return ctx => {
    const { chart } = ctx, area = chart.chartArea;
    if (!area) return color + "33";
    const g = chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
    g.addColorStop(0, color + Math.round(a * 255).toString(16).padStart(2, "0")); g.addColorStop(1, color + "00");
    return g;
  };
}
const lineDs = (label, data, color, extra = {}) => ({ type: "line", label, data, borderColor: color, backgroundColor: grad(color), fill: true, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2, tension: .35, ...extra });
const timeAxis = { type: "linear", grid: { display: false }, ticks: { callback: v => hhmm(v), maxTicksLimit: 6 } };
const elapsedAxis = { type: "linear", grid: { display: false }, ticks: { callback: v => mss(v), maxTicksLimit: 6 } };
// Round tick steps: whole minutes for activities, whole hours for days.
const ELAPSED_STEPS = [60, 120, 300, 600, 900, 1800, 3600, 7200];
const CLOCK_STEPS = [900e3, 1800e3, 3600e3, 7200e3, 10800e3, 14400e3];
function niceX(x, datasets) {
  const xs = datasets.flatMap(d => d.data.map(p => p.x)).filter(v => v != null);
  if (!xs.length) return x;
  const span = Math.max(...xs) - Math.min(...xs), steps = x === elapsedAxis ? ELAPSED_STEPS : CLOCK_STEPS;
  const step = steps.find(s => span / s <= 6) || steps[steps.length - 1];
  return { ...x, ticks: { ...x.ticks, stepSize: step, maxTicksLimit: 8 } };
}
function timeChart(scope, el, datasets, { y = {}, x = timeAxis, legend = false, tooltipTitle = items => hhmm(items[0].parsed.x), plugins = [] } = {}) {
  return mk(scope, el, {
    data: { datasets }, plugins, options: {
      parsing: false, normalized: true,
      scales: { x: niceX(x, datasets), y: { grid: { color: "rgba(255,255,255,.05)" }, ...y } },
      plugins: { legend: { display: legend }, tooltip: { callbacks: { title: tooltipTitle } } },
    },
  });
}
const xy = series => (series || []).map(p => ({ x: p[0], y: p[1] }));

// ---- state & data ----------------------------------------------------------------
let S = null;          // /api/summary
let fresh = null;      // top-line freshness
const PAGES = ["today", "sleep", "activities", "trends"];
let tab = "today", sleepDay = null, trendDays = 30;
try { trendDays = Number(localStorage.getItem("days")) || 30; } catch (e) {}

function renderFresh() {
  if (!fresh) return;
  const parts = [fresh.watch ? T.watchAgo(T.ago(minsSince(fresh.watch))) : T.noSync];
  if (fresh.checked) parts.push(T.checked(T.ago(minsSince(fresh.checked))));
  document.querySelectorAll(".fresh").forEach(el => { el.textContent = parts.join(" · "); el.classList.toggle("stale", !!fresh.stale); });
}
setInterval(renderFresh, 30000);

async function loadSummary(force = false) {
  S = await get("/api/summary", force);
  const f = S.freshness;
  fresh = { watch: f.last_watch_sync, checked: f.last_run && f.last_run.finished_at, stale: f.stale };
  const alert = $("alert"), lr = f.last_run && f.last_run.status;
  if (["login_needed", "error", "rate_limited"].includes(lr)) { alert.className = "alert err on"; alert.textContent = T.lastRun(lr); }
  else if (f.stale && f.hours_since_sync != null) { alert.className = "alert on"; alert.textContent = T.stale(Math.round(f.hours_since_sync)); }
  else alert.className = "alert";
  return S;
}

// ---- today -------------------------------------------------------------------------
function tile(key, val, unit, note, viz, { color, wide = false, ring = null } = {}) {
  const c = color || `var(--${key})`;
  return `<a class="tile tap${wide ? " wide" : ""}" href="#m/${key}" style="--c:${c}">
    <div class="lbl">${svgI(key, "")}${T.m[key]}</div>
    ${ring != null ? `<div class="ring mini-ring">${ringSvg(ring, css(`--${key}`), 12)}</div>` : ""}
    <div class="val"><span class="num">${val}</span>${unit ? `<small>${unit}</small>` : ""}</div>
    <div class="note">${note || "&nbsp;"}</div>
    <div class="viz">${viz || ""}</div></a>`;
}

async function renderToday() {
  const el = $("p-today");
  const [s, tr] = await Promise.all([loadSummary(), get("/api/trends?days=14")]);
  const t = s.today || {}, r = s.recovery, b = s.baseline_30d, y = s.yesterday_activity, fit = s.fitness || {};
  const day = await get(`/api/day/${s.recovery_date || s.date}`);
  const now = new Date();
  const [head, sub] = T[r.label] || T.unknown;
  const chips = [];
  const lo = t.hrv_baseline_low, hi = t.hrv_baseline_high, hrv = t.hrv_last_night;
  if (hrv != null && lo != null) chips.push(hrv < lo ? ["neg", T.hrvLow] : hrv > hi ? ["pos", T.hrvHigh] : ["pos", T.hrvOk]);
  if (t.sleep_seconds != null && t.sleep_seconds < 6 * 3600) chips.push(["neg", T.shortSleep]); else if (t.sleep_score >= 85) chips.push(["pos", T.greatSleep]);
  if (t.resting_hr != null && b.resting_hr != null) { const d = t.resting_hr - b.resting_hr; if (d >= 3) chips.push(["neg", T.rhrHigh]); else if (d <= -3) chips.push(["pos", T.rhrLow]); }
  const bbWake = t.bb_wake ?? t.bb_high;
  if (bbWake != null) { if (bbWake < 40) chips.push(["neg", T.bbLow]); else if (bbWake >= 85) chips.push(["pos", T.bbHigh]); }
  if (t.acwr_status === "HIGH") chips.push(["neg", T.rampUp]);
  const rc = css(`--${r.label === "unknown" ? "faint" : r.label}`);

  const sl = day.sleep, hrvSeries = sl ? vals(sl.hrv) : [];
  const bbSeries = day.body_battery.length ? day.body_battery : (sl ? sl.body_battery : []);
  const stressSeries = day.stress.length ? day.stress : [];
  const stepsVals = day.steps.map(p => p[1]);
  const vo2 = fit.vo2max ?? fit.vo2max_estimate;
  const tiles = [
    tile("sleep", hm(t.sleep_seconds), "", t.sleep_score != null ? `${T.score} ${t.sleep_score}` : "", hypnogram(sl, { h: 46, labels: false }), { wide: true }),
    tile("hrv", n0(hrv), T.ms, T.hrvStatus[t.hrv_status] || (t.hrv_status || "").toLowerCase(), spark(hrvSeries.slice(-60), css("--hrv"))),
    tile("rhr", n0(t.resting_hr), T.bpm, b.resting_hr != null ? `${T.avg} ${n0(b.resting_hr)}` : "", spark(tr.resting_hr, css("--rhr"))),
    tile("bb", n0(bbWake), "", T.atWake, spark(vals(bbSeries), css("--bb"), { min: 0, max: 100 })),
    tile("spo2", n0(fit.spo2_sleep_avg), "%", fit.spo2_sleep_low != null ? `${T.lowest} ${fit.spo2_sleep_low}%` : "", spark(vals(sl && sl.spo2), css("--spo2"), { area: false, dot: false })),
    tile("stress", n0(y.stress_avg), "", y.stress_avg != null ? T.stressLv(y.stress_avg) : "", stressSeries.length ? bars(stressSeries.map(p => p[1]).filter((_, i) => i % 3 === 0), v => v <= 25 ? css("--bb") : css("--stress")) : spark(tr.stress, css("--stress"))),
    tile("steps", n0(y.steps), "", y.step_goal ? `${T.goal} ${n0(y.step_goal)}` : "", stepsVals.length ? bars(stepsVals, () => css("--steps")) : bars(tr.steps.map(v => v || 0), () => css("--steps")), { ring: y.step_goal ? 100 * y.steps / y.step_goal : null }),
    tile("readiness", n0(t.readiness_score), "", T.levels[t.readiness_level] || (t.readiness_level || "").toLowerCase(), "", { ring: t.readiness_score }),
    tile("resp", n0(sl && sl.avg_respiration), T.perMin, T.night, spark(vals(sl && sl.respiration), css("--resp"), { area: false, dot: false })),
    tile("fitness", fit.fitness_age != null ? fit.fitness_age.toFixed(1) : "–", "", fit.chronological_age ? T.actual(fit.chronological_age) : "", fitScale(fit)),
    tile("vo2", vo2 != null ? (fit.vo2max == null ? "≈" : "") + vo2.toFixed(1) : "–", "", fit.vo2max == null && vo2 != null ? T.estimate : "", "", { wide: false }),
  ];
  const acts = s.activities_7d.slice().reverse().slice(0, 3);
  el.innerHTML = `
    <h1 class="large" data-title>${T.today}</h1>
    <div class="subtitle"><span>${T.longDays[now.getDay()]} ${now.getDate()}.${now.getMonth() + 1}</span> · <span class="fresh"></span></div>
    <div class="hero">
      <div class="ring">${ringSvg(r.score, rc, 9)}<div class="in"><b class="num"><span id="rec-n">–</span><sup>%</sup></b><span>${T.recovery}</span></div></div>
      <div class="headline">${head}</div><p class="sub">${sub}</p>
      <div class="chips">${chips.slice(0, 3).map(([c, x]) => `<span class="chip ${c}">${x}</span>`).join("")}</div>
      ${s.recovery_date && s.recovery_date !== s.date ? `<div class="basis">${T.basis(dm(s.recovery_date))}</div>` : ""}
    </div>
    <div class="section">${T.yourMetrics}</div>
    <div class="tiles">${tiles.join("")}</div>
    <div class="section">${T.recentActs}<a href="#activities">${T.all}</a></div>
    <div class="card">${acts.length ? acts.map(actRow).join("") : `<div class="empty">${T.noActs}</div>`}</div>`;
  renderFresh();
  countUp($("rec-n"), r.score);
  animateIn(el);
}
function fitScale(fit) {
  if (fit.fitness_age == null || fit.chronological_age == null || fit.achievable_fitness_age == null) return "";
  const lo = Math.min(fit.achievable_fitness_age, fit.fitness_age) - 2, hi = Math.max(fit.chronological_age, fit.fitness_age) + 2;
  const X = v => ((v - lo) / (hi - lo)) * 200;
  return `<svg viewBox="0 0 200 46" preserveAspectRatio="none" direction="ltr">
    <rect x="0" y="27" width="200" height="6" rx="3" fill="rgba(255,255,255,.08)"/>
    <rect x="${X(fit.achievable_fitness_age)}" y="27" width="${X(fit.chronological_age) - X(fit.achievable_fitness_age)}" height="6" rx="3" fill="${css("--fit")}" opacity=".35"/>
    <rect x="${X(fit.chronological_age) - 1}" y="22" width="2" height="16" rx="1" fill="#8e8e93"/>
    <circle cx="${X(fit.fitness_age)}" cy="30" r="6" fill="${css("--fit")}" stroke="#121316" stroke-width="2.5"/></svg>`;
}
function actRow(a) {
  const k = actKind(a.type || ""), bits = [a.distance_m ? `${(a.distance_m / 1000).toFixed(2)} ${T.km}` : "", mss(a.duration_s), a.avg_hr ? `${Math.round(a.avg_hr)} ${T.bpm}` : ""].filter(Boolean);
  return `<a class="act tap" href="#a/${a.activity_id}" style="--c:var(${actColor(a.type || "")})">
    <div class="ic">${svgI(k, "")}</div>
    <div><b>${esc(actName(a))}</b><small>${dm(a.date)} · ${bits.map(x => `<span class="num">${x}</span>`).join(" · ")}</small></div>
    <div class="load">${a.training_load ? `<b class="num">${Math.round(a.training_load)}</b><small>${T.load}</small>` : ""}</div></a>`;
}

// ---- sleep page ----------------------------------------------------------------------
function dayNav(ds, onChange) {
  const id = "dn" + Math.random().toString(36).slice(2, 7);
  setTimeout(() => {
    const root = $(id); if (!root) return;
    root.querySelector("[data-d='-1']").onclick = () => onChange(addDays(ds, -1));
    const nx = root.querySelector("[data-d='1']"); nx.disabled = ds >= todayIso(); nx.onclick = () => onChange(addDays(ds, 1));
  });
  const arrow = '<svg viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></svg>', arrowR = '<svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>';
  return `<div class="daynav" id="${id}"><button data-d="-1">${arrow}</button><b>${dayLabel(ds)}</b><button data-d="1">${arrowR}</button></div>`;
}
function statBox(label, val, unit = "") { return `<div class="stat"><small>${label}</small><b class="num">${val}${unit ? `<small>${unit}</small>` : ""}</b></div>`; }

async function renderSleep(ds) {
  sleepDay = ds || sleepDay || (S && S.recovery_date) || todayIso();
  const el = $("p-sleep");
  killCharts("page");
  const d = await get(`/api/day/${sleepDay}`);
  const sl = d.sleep, row = d.row || {};
  const head = `<h1 class="large" data-title>${T.sleep}</h1><div class="subtitle fresh"></div>${dayNav(sleepDay, x => { renderSleep(x); })}`;
  if (!sl) { el.innerHTML = head + `<div class="card"><div class="empty">${T.noData}</div></div>`; renderFresh(); return; }
  const total = row.sleep_seconds, st = { deep: row.deep_seconds, light: row.light_seconds, rem: row.rem_seconds, awake: row.awake_seconds };
  const sum = Object.values(st).reduce((a, b) => a + (b || 0), 0) || 1;
  const hrS = statsOf(sl.hr), spS = statsOf(sl.spo2), hvS = statsOf(sl.hrv), reS = statsOf(sl.respiration);
  el.innerHTML = head + `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px">
        <div><div class="big-val num" style="margin:0">${hm(total)}</div>
          <div class="explain" style="margin:4px 0 0"><span class="num">${hhmm(sl.start)} – ${hhmm(sl.end)}</span>${T.sleepFb(sl.feedback) ? ` · ${T.sleepFb(sl.feedback)}` : ""}</div></div>
        <div class="ring" style="width:84px;height:84px">${ringSvg(row.sleep_score, css("--sleep"), 10)}<div class="in"><b class="num" style="font-size:26px">${n0(row.sleep_score)}</b><span style="font-size:11px;color:var(--muted)">${T.score}</span></div></div>
      </div>
      ${sl.need_minutes ? `<div class="explain" style="margin:10px 0 0">${T.need(hm(sl.need_minutes * 60))}</div>` : ""}
    </div>
    <div class="card"><h3>${T.t_sleepStages}</h3>${hypnogram(sl)}
      <div class="stagebars">${["deep", "light", "rem", "awake"].map(k => `<div class="stagebar"><span>${T[k]}</span>
        <div class="bar"><i data-w="${(100 * (st[k] || 0)) / sum}" style="background:var(--${k})"></i></div><b class="num">${hm(st[k])}</b></div>`).join("")}</div></div>
    <div class="stats">${statBox(T.avgHr, n0(hrS && hrS.avg), T.bpm)}${statBox(T.lowest, n0(hrS && hrS.min), T.bpm)}${statBox("HRV", n0(hvS && hvS.avg), T.ms)}
      ${statBox(T.m.spo2, n0(spS && spS.avg), "%")}${statBox(T.resp, n1(reS && reS.avg), T.perMin)}${statBox(T.restless, n0(sl.restless))}</div>
    <div class="card"><h3>${T.hrNight}</h3><div class="chart short"><canvas id="c-shr"></canvas></div></div>
    <div class="card"><h3>${T.hrvNight}</h3><div class="chart short"><canvas id="c-shrv"></canvas></div></div>
    <div class="card"><h3>${T.spo2Night}</h3><div class="chart short"><canvas id="c-sspo2"></canvas></div></div>
    <div class="card"><h3>${T.respNight}</h3><div class="chart short"><canvas id="c-sresp"></canvas></div></div>
    <div class="card"><h3>${T.bbNight}</h3><div class="chart short"><canvas id="c-sbb"></canvas></div></div>`;
  renderFresh();
  animateIn(el);
  timeChart("page", $("c-shr"), [lineDs(T.hrChart, xy(sl.hr), css("--rhr"))]);
  timeChart("page", $("c-shrv"), [lineDs("HRV", xy(sl.hrv), css("--hrv"))]);
  timeChart("page", $("c-sspo2"), [lineDs(T.m.spo2, xy(sl.spo2), css("--spo2"), { tension: .2 })], { y: { suggestedMin: 85, max: 100 } });
  timeChart("page", $("c-sresp"), [lineDs(T.resp, xy(sl.respiration), css("--resp"))]);
  timeChart("page", $("c-sbb"), [
    lineDs("Body Battery", xy(sl.body_battery), css("--bb")),
    lineDs(T.m.stress, xy(sl.stress), css("--stress"), { fill: false, borderWidth: 1.5 }),
  ], { y: { min: 0, max: 100 }, legend: true });
}

// ---- activities page ---------------------------------------------------------------------
async function renderActivities() {
  const el = $("p-activities");
  const acts = await get("/api/activities?days=365");
  const groups = [];
  for (const a of acts) {
    const d = new Date(a.date + "T12:00"); d.setDate(d.getDate() - d.getDay());
    const wk = isoDay(d);
    if (!groups.length || groups[groups.length - 1].wk !== wk) groups.push({ wk, items: [] });
    groups[groups.length - 1].items.push(a);
  }
  const thisWeek = (() => { const d = new Date(); d.setDate(d.getDate() - d.getDay()); return isoDay(d); })();
  el.innerHTML = `<h1 class="large" data-title>${T.acts}</h1><div class="subtitle fresh"></div>` + (groups.length ? groups.map(g => `
    <div class="weekhead">${g.wk === thisWeek ? T.thisWeek : T.weekOf(dm(g.wk))}</div>
    <div class="card">${g.items.map(actRow).join("")}</div>`).join("") : `<div class="card"><div class="empty">${T.noActs}</div></div>`);
  renderFresh();
}

// ---- trends page ---------------------------------------------------------------------------
async function renderTrends() {
  const el = $("p-trends");
  killCharts("page");
  const d = await get(`/api/trends?days=${trendDays}`);
  const labels = d.dates.map(dm), f = S ? S.freshness : {};
  const card = (title, id) => `<div class="card"><h3>${title}</h3><div class="chart"><canvas id="${id}"></canvas></div></div>`;
  el.innerHTML = `<h1 class="large" data-title>${T.trends}</h1><div class="subtitle fresh"></div>
    <div class="seg" id="tseg">${[7, 30, 90].map(n => `<button data-n="${n}" class="${n === trendDays ? "on" : ""}">${n}</button>`).join("")}</div>
    ${card(T.t_sleepStages, "t-sleep")}${card(T.t_hrv, "t-hrv")}${card(T.t_rhr, "t-rhr")}${card(T.t_bb, "t-bb")}
    ${card(T.t_spo2, "t-spo2")}${card(T.t_stress, "t-stress")}${card(T.t_steps, "t-steps")}${card(T.t_load, "t-load")}
    <div class="section">${T.settings}</div>
    <div class="card settings">
      <div class="row"><span>${T.language}</span><a href="${OTHER_LANG_URL}">${LANG === "he" ? "English" : "עברית"}</a></div>
      <div class="row"><span>${T.device}</span><small>${esc(f.device || "–")}</small></div>
      <div class="row"><span class="fresh" style="font-size:14px;color:var(--muted)"></span></div>
      <div class="row"><span>${T.syncNow}</span><button id="tsync">↻</button></div>
    </div>`;
  renderFresh();
  el.querySelectorAll("#tseg button").forEach(b => b.onclick = () => { trendDays = +b.dataset.n; try { localStorage.setItem("days", trendDays); } catch (e) {} renderTrends(); });
  $("tsync").onclick = sync;
  const base = { scales: { x: { grid: { display: false } }, y: { grid: { color: "rgba(255,255,255,.05)" } } } };
  const bar = (label, data, color, extra = {}) => ({ type: "bar", label, data, backgroundColor: color, borderRadius: 3, ...extra });
  const ln = (label, data, color, extra = {}) => ({ type: "line", label, data, borderColor: color, backgroundColor: grad(color, .25), fill: false, pointRadius: trendDays <= 30 ? 2 : 0, borderWidth: 2, tension: .35, ...extra });
  mk("page", $("t-sleep"), { data: { labels, datasets: [bar(T.deep, d.sleep.deep, css("--deep"), { stack: "s" }), bar(T.light, d.sleep.light, css("--light"), { stack: "s" }), bar(T.rem, d.sleep.rem, css("--rem"), { stack: "s" }), bar(T.awake, d.sleep.awake, css("--awake"), { stack: "s" })] },
    options: { ...base, scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, grid: { color: "rgba(255,255,255,.05)" } } } } });
  mk("page", $("t-hrv"), { data: { labels, datasets: [ln(T.lastNight, d.hrv.last_night, css("--hrv")), ln(T.weekly, d.hrv.weekly_avg, "#d1d1d6", { borderDash: [4, 3], borderWidth: 1.5, pointRadius: 0 }),
    ln(T.range, d.hrv.baseline_low, "transparent", { pointRadius: 0, backgroundColor: "rgba(48,209,88,.12)" }), ln(T.range, d.hrv.baseline_high, "transparent", { pointRadius: 0, backgroundColor: "rgba(48,209,88,.12)", fill: "-1" })] },
    options: { ...base, plugins: { legend: { labels: { filter: it => it.datasetIndex < 2 } } } } });
  mk("page", $("t-rhr"), { data: { labels, datasets: [ln(T.t_rhr, d.resting_hr, css("--rhr"), { fill: true })] }, options: { ...base, plugins: { legend: { display: false } } } });
  mk("page", $("t-bb"), { data: { labels, datasets: [bar(T.range, d.body_battery.high.map((h, i) => h == null ? null : [d.body_battery.low[i] ?? 0, h]), "rgba(64,200,224,.35)"), ln(T.atWake, d.body_battery.wake, css("--bb"))] },
    options: { ...base, scales: { ...base.scales, y: { min: 0, max: 100, grid: { color: "rgba(255,255,255,.05)" } } } } });
  mk("page", $("t-spo2"), { data: { labels, datasets: [ln(T.avg, d.spo2.sleep_avg, css("--spo2")), ln(T.lowest, d.spo2.sleep_low, "#d1d1d6", { borderDash: [4, 3], borderWidth: 1.5 })] },
    options: { ...base, scales: { ...base.scales, y: { suggestedMin: 80, max: 100, grid: { color: "rgba(255,255,255,.05)" } } } } });
  mk("page", $("t-stress"), { data: { labels, datasets: [bar(T.t_stress, d.stress, d.stress.map(v => v == null ? null : v <= 25 ? css("--bb") : css("--stress")))] }, options: { ...base, plugins: { legend: { display: false } } } });
  mk("page", $("t-steps"), { data: { labels, datasets: [bar(T.t_steps, d.steps, css("--steps"))] }, options: { ...base, plugins: { legend: { display: false } } } });
  mk("page", $("t-load"), { data: { labels, datasets: [bar(T.daily, d.training_load.daily, "rgba(255,159,10,.55)"), ln(T.acute, d.training_load.acute, css("--stress")), ln(T.chronic, d.training_load.chronic, "#d1d1d6", { borderDash: [4, 3], borderWidth: 1.5, pointRadius: 0 })] }, options: base });
}

// ---- metric detail sheet ------------------------------------------------------------------
const sheet = $("sheet");
function openSheet(html, color) {
  killCharts("sheet");
  sheet.style.setProperty("--c", color || "#0a84ff");
  sheet.innerHTML = `<div class="nav"><button class="back" id="sback"><svg viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6"/></svg>${T[tab === "activities" ? "acts" : tab] || T.back}</button></div><div class="body">${html}</div>`;
  $("sback").onclick = closeSheet;
  sheet.scrollTop = 0;
  sheet.classList.add("open"); document.body.classList.add("sheet-open");
  animateIn(sheet);
}
function closeSheet() {
  if (history.state && history.state.inApp) history.back(); else location.hash = tab;
}
function hideSheet() { sheet.classList.remove("open"); document.body.classList.remove("sheet-open"); setTimeout(() => { if (!sheet.classList.contains("open")) { killCharts("sheet"); sheet.innerHTML = ""; } }, 450); }

async function openMetric(key, ds) {
  if (key === "sleep") { location.replace(`#sleep`); return; }
  if (!S) await loadSummary();
  ds = ds || S.recovery_date || todayIso();
  const [d, tr] = await Promise.all([get(`/api/day/${ds}`), get("/api/trends?days=30")]);
  const color = css(`--${key}`), sl = d.sleep, row = d.row || {}, fit = S.fitness || {};
  const nav = dayNav(ds, x => openMetric(key, x));
  const header = (val, unit, note = "") => `<div class="big-head" style="--c:${color}"><div class="ic">${svgI(key, "")}</div><div><div style="font-size:28px;font-weight:700;letter-spacing:-.02em">${T.m[key]}</div></div></div>
    <div class="big-val num" style="color:${color}">${val}${unit ? `<small>${unit}</small>` : ""}</div>${note ? `<div class="explain" style="margin:0 0 6px">${note}</div>` : ""}`;
  const ex = `<div class="explain">${T.ex[key] || ""}</div>`;
  const chartCard = (title, id, cls = "") => `<div class="card"><h3>${title}</h3><div class="chart ${cls}"><canvas id="${id}"></canvas></div></div>`;
  let html = "", after = () => {};
  const trendChart = (id, data, extra = {}) => mk("sheet", $(id), { data: { labels: tr.dates.map(dm), datasets: [{ type: "line", data, borderColor: color, backgroundColor: grad(color, .3), fill: true, pointRadius: 2, borderWidth: 2, tension: .35, ...extra }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { grid: { color: "rgba(255,255,255,.05)" } } } } });
  const stats3 = s => s ? `<div class="stats">${statBox(T.min, n0(s.min))}${statBox(T.avg, n0(s.avg))}${statBox(T.max, n0(s.max))}</div>` : "";
  const missing = `<div class="card"><div class="empty">${d.has_intraday ? T.noData : T.noIntraday}</div></div>`;

  if (key === "hrv") {
    const s = statsOf(sl && sl.hrv);
    html = header(n0(row.hrv_last_night), T.ms, row.hrv_baseline_low != null ? `${T.range} ${n0(row.hrv_baseline_low)}–${n0(row.hrv_baseline_high)} · ${T.hrvStatus[row.hrv_status] || row.hrv_status || ""}` : "") + ex + nav + stats3(s)
      + (sl && sl.hrv.length ? chartCard(T.hrvNight, "m-a") : missing) + chartCard(`${T.trend} · 30`, "m-t");
    after = () => {
      if (sl && sl.hrv.length) timeChart("sheet", $("m-a"), [lineDs("HRV", xy(sl.hrv), color)]);
      mk("sheet", $("m-t"), { data: { labels: tr.dates.map(dm), datasets: [
        { type: "line", data: tr.hrv.last_night, borderColor: color, pointRadius: 2, borderWidth: 2, tension: .35 },
        { type: "line", data: tr.hrv.baseline_low, borderColor: "transparent", pointRadius: 0, backgroundColor: color + "22" },
        { type: "line", data: tr.hrv.baseline_high, borderColor: "transparent", pointRadius: 0, backgroundColor: color + "22", fill: "-1" }] },
        options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { grid: { color: "rgba(255,255,255,.05)" } } } } });
    };
  } else if (key === "rhr") {
    const series = d.hr.length ? d.hr : (sl ? sl.hr : []), s = statsOf(series);
    html = header(n0(row.resting_hr), T.bpm, S.baseline_30d.resting_hr != null ? `${T.avg} 30: ${n0(S.baseline_30d.resting_hr)}` : "") + ex + nav + stats3(s)
      + (series.length ? chartCard(d.hr.length ? `${T.hrChart} · ${T.dayTime}` : T.hrNight, "m-a", "tall") : missing) + chartCard(`${T.t_rhr} · 30`, "m-t");
    after = () => { if (series.length) timeChart("sheet", $("m-a"), [lineDs(T.hrChart, xy(series), color, { tension: .2, borderWidth: 1.6 })]); trendChart("m-t", tr.resting_hr); };
  } else if (key === "bb") {
    const series = d.body_battery.length ? d.body_battery : (sl ? sl.body_battery : []), s = statsOf(series);
    html = header(n0(row.bb_wake ?? row.bb_high), "", `${T.atWake} · ${T.high} ${n0(row.bb_high)} · ${T.min} ${n0(row.bb_low)}`) + ex + nav + stats3(s)
      + (series.length ? chartCard(d.body_battery.length ? T.dayTime : T.night, "m-a", "tall") : missing) + chartCard(`${T.trend} · 30`, "m-t");
    after = () => {
      if (series.length) timeChart("sheet", $("m-a"), [lineDs("Body Battery", xy(series), color, { stepped: false, tension: .3 })], { y: { min: 0, max: 100 } });
      trendChart("m-t", tr.body_battery.wake, { fill: false });
    };
  } else if (key === "spo2") {
    const s = statsOf(sl && sl.spo2);
    html = header(n0(row.spo2_sleep_avg), "%", row.spo2_sleep_low != null ? `${T.lowest} ${row.spo2_sleep_low}% · ${T.night}` : "") + ex + nav + stats3(s)
      + (sl && sl.spo2.length ? chartCard(T.spo2Night, "m-a", "tall") : missing) + chartCard(`${T.trend} · 30`, "m-t");
    after = () => {
      if (sl && sl.spo2.length) timeChart("sheet", $("m-a"), [lineDs(T.m.spo2, xy(sl.spo2), color, { tension: .15, borderWidth: 1.6 })], { y: { suggestedMin: 85, max: 100 } });
      trendChart("m-t", tr.spo2.sleep_avg);
    };
  } else if (key === "stress") {
    const series = d.stress.length ? d.stress : (sl ? sl.stress : []), s = statsOf(series);
    html = header(n0(row.stress_avg), "", row.stress_avg != null ? T.stressLv(row.stress_avg) : "") + ex + nav + stats3(s)
      + (series.length ? chartCard(d.stress.length ? T.dayTime : T.night, "m-a", "tall") : missing) + chartCard(`${T.trend} · 30`, "m-t");
    after = () => {
      if (series.length) timeChart("sheet", $("m-a"), [{ type: "bar", label: T.m.stress, data: xy(series), backgroundColor: series.map(p => p[1] <= 25 ? css("--bb") : p[1] <= 50 ? "#ffb340" : p[1] <= 75 ? css("--stress") : "#ff6b2c"), barPercentage: 1, categoryPercentage: 1 }], { y: { min: 0, max: 100 } });
      mk("sheet", $("m-t"), { data: { labels: tr.dates.map(dm), datasets: [{ type: "bar", data: tr.stress, backgroundColor: color, borderRadius: 3 }] }, options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } } } } });
    };
  } else if (key === "steps") {
    const total = d.steps.reduce((a, p) => a + (p[1] || 0), 0) || row.steps;
    html = header(n0(total), "", row.step_goal ? `${T.goal} ${n0(row.step_goal)}` : "") + ex + nav
      + (d.steps.length ? chartCard(T.dayTime, "m-a", "tall") : missing) + chartCard(`${T.trend} · 30`, "m-t");
    after = () => {
      if (d.steps.length) timeChart("sheet", $("m-a"), [{ type: "bar", label: T.m.steps, data: xy(d.steps), backgroundColor: color, borderRadius: 2, barPercentage: .9, categoryPercentage: 1 }]);
      mk("sheet", $("m-t"), { data: { labels: tr.dates.map(dm), datasets: [{ type: "bar", data: tr.steps, backgroundColor: color, borderRadius: 3 }] }, options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } } } } });
    };
  } else if (key === "resp") {
    const s = statsOf(sl && sl.respiration);
    html = header(n1(sl && sl.avg_respiration), T.perMin, T.night) + ex + nav + (s ? `<div class="stats">${statBox(T.min, n1(s.min))}${statBox(T.avg, n1(s.avg))}${statBox(T.max, n1(s.max))}</div>` : "")
      + (sl && sl.respiration.length ? chartCard(T.respNight, "m-a", "tall") : missing);
    after = () => { if (sl && sl.respiration.length) timeChart("sheet", $("m-a"), [lineDs(T.resp, xy(sl.respiration), color)]); };
  } else if (key === "readiness") {
    const rd = d.readiness;
    html = header(n0(rd ? rd.score : row.readiness_score), "", T.levels[row.readiness_level] || row.readiness_level || "") + ex + nav
      + (rd && Object.keys(rd.factors).length ? `<div class="card"><h3>${T.factors}</h3>${Object.entries(rd.factors).map(([k, f]) => `<div class="factor">
          <span>${T.rf[k] || k}</span><small>${T.fb[f.feedback] || f.feedback || ""}</small>
          <div class="bar"><i data-w="${f.percent}" style="background:${f.percent >= 70 ? css("--good") : f.percent >= 40 ? css("--fair") : css("--low")}"></i></div></div>`).join("")}</div>` : missing)
      + chartCard(`${T.trend} · 30`, "m-t");
    after = () => trendChart("m-t", tr.readiness);
  } else if (key === "fitness") {
    const fa = d.fitness_age || {}, comps = fa.components || {};
    const diff = fit.chronological_age != null && fit.fitness_age != null ? fit.chronological_age - fit.fitness_age : null;
    html = header(fit.fitness_age != null ? fit.fitness_age.toFixed(1) : "–", "", fit.chronological_age ? `${T.actual(fit.chronological_age)}${diff != null ? " · " + (diff >= 0 ? T.younger(diff.toFixed(1)) : T.older((-diff).toFixed(1))) : ""}` : "") + ex
      + `<div class="card"><div class="viz" style="height:46px">${fitScale(fit)}</div>${fit.achievable_fitness_age != null ? `<div class="explain" style="margin:8px 0 0">${T.achievable(Math.round(fit.achievable_fitness_age))}</div>` : ""}</div>`
      + (Object.keys(comps).length ? `<div class="card"><h3>${T.components}</h3>${Object.entries(comps).sort((a, b) => (a[1].priority || 9) - (b[1].priority || 9)).map(([k, c]) => {
          const pct = c.targetValue ? Math.min(100, k === "bmi" ? 100 * c.targetValue / c.value : 100 * c.value / c.targetValue) : 100;
          return `<div class="factor"><span>${T.fa[k] || k} <b class="num">${n1(c.value)}</b></span><small>${c.targetValue != null ? T.target(n1(c.targetValue)) : ""}${c.potentialAge ? " · " + T.potential(n1(c.potentialAge)) : ""}</small>
            <div class="bar"><i data-w="${pct}" style="background:var(--fit)"></i></div></div>`;
        }).join("")}</div>` : "");
  } else if (key === "vo2") {
    const v = fit.vo2max ?? fit.vo2max_estimate;
    html = header(v != null ? (fit.vo2max == null ? "≈" : "") + v.toFixed(1) : "–", "", fit.vo2max != null ? T.vo2Garmin : "") + ex
      + (fit.vo2max == null ? `<div class="card"><div class="explain" style="margin:0">${T.vo2Est}</div></div>` : "")
      + (tr.vo2max && tr.vo2max.some(x => x != null) ? chartCard(`${T.trend} · 30`, "m-t") : "");
    after = () => { if (tr.vo2max && tr.vo2max.some(x => x != null)) trendChart("m-t", tr.vo2max); };
  }
  openSheet(html, color);
  after();
}

// ---- activity detail sheet ---------------------------------------------------------------
function paceStr(speed, kind) {
  if (!speed) return "–";
  if (kind === "swim") return mss(100 / speed) + T.m100;
  if (kind === "walk") return mss(1000 / speed) + T.perKm;
  return `${(speed * 3.6).toFixed(1)} ${T.kmh}`;
}
async function openActivity(id) {
  const a = await get(`/api/activity/${id}`);
  if (a.error) { toast(a.error); return; }
  const kind = actKind(a.type || ""), color = css(actColor(a.type || "")), s = a.stats || {};
  const start = a.start_local ? new Date(a.start_local.replace(" ", "T")) : null;
  const items = [
    [T.duration, mss(s.duration ?? a.duration_s)], [T.distance, a.distance_m ? `${(a.distance_m / 1000).toFixed(2)}` : null, T.km],
    [kind === "swim" || kind === "walk" ? T.pace : T.speed, s.averageSpeed && kind !== "dive" ? paceStr(s.averageSpeed, kind) : null],
    [T.avgHr, s.averageHR ? n0(s.averageHR) : null, T.bpm], [T.maxHr, s.maxHR ? n0(s.maxHR) : null, T.bpm],
    [T.calories, s.calories ? n0(s.calories) : null], [T.load, s.activityTrainingLoad ? n0(s.activityTrainingLoad) : null],
    [T.aerobic, s.trainingEffect ? n1(s.trainingEffect) : null], [T.anaerobic, s.anaerobicTrainingEffect ? n1(s.anaerobicTrainingEffect) : null],
    [T.swolf, s.averageSWOLF ? n0(s.averageSWOLF) : null], [T.strokes, s.totalNumberOfStrokes ? n0(s.totalNumberOfStrokes) : null],
    [T.maxDepth, s.maxDepth ? n1(s.maxDepth) : null, "m"], [T.avgDepth, s.averageDepth ? n1(s.averageDepth) : null, "m"],
    [T.dives, s.diveCount ? n0(s.diveCount) : null], [T.bottom, s.bottomTime ? mss(s.bottomTime) : null], [T.surface, s.surfaceInterval ? mss(s.surfaceInterval) : null],
    [T.temp, s.averageTemperature != null ? n1(s.averageTemperature) : null, "°"], [T.elev, s.elevationGain && kind !== "dive" && kind !== "swim" ? n0(s.elevationGain) : null, "m"],
    [T.moving, s.movingDuration ? mss(s.movingDuration) : null], [T.bbDiff, s.differenceBodyBattery != null ? (s.differenceBodyBattery > 0 ? "+" : "") + s.differenceBodyBattery : null],
    [T.intensity, (s.moderateIntensityMinutes || s.vigorousIntensityMinutes) ? n0((s.moderateIntensityMinutes || 0) + 2 * (s.vigorousIntensityMinutes || 0)) : null],
  ].filter(x => x[1] != null && x[1] !== "–");
  const ser = a.series || {}, t = a.t || [];
  const pts = key => t.map((x, i) => ({ x, y: ser[key] ? ser[key][i] : null })).filter(p => p.x != null && p.y != null);
  const zoneColors = ["#8e8e93", "#0a84ff", "#30d158", "#ff9f0a", "#ff453a"];
  const zones = a.hr_zones, zt = zones ? zones.reduce((x, y) => x + y, 0) || 1 : 1;
  const card = (title, id, cls = "") => `<div class="card"><h3>${title}</h3><div class="chart ${cls}"><canvas id="${id}"></canvas></div></div>`;
  const html = `
    <div class="big-head" style="--c:${color}"><div class="ic">${svgI(kind, "")}</div>
      <div><div style="font-size:26px;font-weight:700;letter-spacing:-.02em;line-height:1.15">${esc(actName(a))}</div>
      <div class="explain" style="margin:2px 0 0">${start ? `${T.longDays[start.getDay()]} ${start.getDate()}.${start.getMonth() + 1} · ${hhmm(start.getTime())}` : ""}${a.location ? " · " + esc(a.location) : ""}</div></div></div>
    ${a.name && T.types[a.type] && a.name !== T.types[a.type] ? `<div class="explain">${esc(a.name)}</div>` : ""}
    <div class="stats" style="margin-top:14px">${items.map(([l, v, u]) => statBox(l, v, u)).join("")}</div>
    ${a.route.length > 1 ? `<div class="card"><h3>${T.route}</h3>${routeSvg(a.route)}</div>` : ""}
    ${ser.hr ? card(T.hrChart, "a-hr", "tall") : ""}
    ${zones ? `<div class="card"><h3>${T.hrZones}</h3><div class="zones">${zones.map((z, i) => `<div class="zone"><span class="num">Z${i + 1}</span>
      <div class="bar"><i data-w="${(100 * z) / zt}" style="background:${zoneColors[i]}"></i></div><b class="num">${mss(z)}</b></div>`).join("")}</div>
      <div class="explain" style="margin:10px 0 0">${T.zonesNote(Math.round(a.hr_max_used))}</div></div>` : ""}
    ${ser.depth ? card(T.depthChart, "a-depth", "tall") : ""}
    ${ser.speed && kind !== "dive" ? card(T.speedChart, "a-speed") : ""}
    ${ser.cadence ? card(T.cadenceChart, "a-cad", "short") : ""}
    ${ser.temp ? card(T.tempChart, "a-temp", "short") : ""}
    ${a.laps.length > 1 ? `<div class="card"><h3>${T.laps}</h3><table class="laps"><tr><th>${T.lap}</th><th>${T.distance}</th><th>${T.duration}</th><th>${T.avgHr}</th>${kind === "swim" ? `<th>${T.swolf}</th>` : ""}</tr>
      ${a.laps.map(l => `<tr><td>${(l.lapIndex ?? 0) + 1}</td><td>${l.distance ? (l.distance / 1000).toFixed(2) : "–"}</td><td>${mss(l.duration)}</td><td>${n0(l.averageHR)}</td>${kind === "swim" ? `<td>${n0(l.averageSWOLF)}</td>` : ""}</tr>`).join("")}</table></div>` : ""}`;
  openSheet(html, color);
  if (ser.hr) {
    const hrMax = a.hr_max_used || 190;
    const zonesPlugin = { id: "zones", beforeDraw(c) {
      const { ctx, chartArea: ar, scales: { y } } = c; if (!ar) return;
      [.5, .6, .7, .8, .9].forEach((p, i) => {
        const top = y.getPixelForValue(Math.min(hrMax * (p + .1), y.max)), bot = y.getPixelForValue(Math.max(hrMax * p, y.min));
        if (bot < ar.top || top > ar.bottom) return;
        ctx.fillStyle = zoneColors[i] + "14"; ctx.fillRect(ar.left, Math.max(top, ar.top), ar.right - ar.left, Math.min(bot, ar.bottom) - Math.max(top, ar.top));
      });
    } };
    timeChart("sheet", $("a-hr"), [lineDs(T.hrChart, pts("hr"), css("--rhr"), { tension: .2, borderWidth: 1.8 })], { x: elapsedAxis, tooltipTitle: it => mss(it[0].parsed.x), plugins: [zonesPlugin] });
  }
  if (ser.depth) timeChart("sheet", $("a-depth"), [lineDs(T.depthChart, pts("depth"), color, { tension: .2, fill: "origin", backgroundColor: grad(color, .45) })], { x: elapsedAxis, y: { reverse: true, min: 0 }, tooltipTitle: it => mss(it[0].parsed.x) });
  if (ser.speed && kind !== "dive") {
    const sp = pts("speed").map(p => ({ x: p.x, y: kind === "swim" ? (p.y > .05 ? 100 / p.y : null) : kind === "walk" ? (p.y > .3 ? 1000 / p.y : null) : p.y * 3.6 })).filter(p => p.y != null);
    const isPace = kind === "swim" || kind === "walk";
    // Pace: faster is higher on the chart; stops and pauses are clipped off.
    const sorted = sp.map(p => p.y).sort((m, n) => m - n), median = sorted[Math.floor(sorted.length / 2)] || 0;
    timeChart("sheet", $("a-speed"), [lineDs(T.speedChart, sp, color, { tension: .3, borderWidth: 1.6, fill: !isPace })], {
      x: elapsedAxis, tooltipTitle: it => mss(it[0].parsed.x),
      y: isPace ? { reverse: true, min: Math.floor(sorted[0] * .9), max: Math.ceil(median * 1.8), ticks: { callback: v => mss(v) } } : {},
    });
  }
  if (ser.cadence) timeChart("sheet", $("a-cad"), [lineDs(T.cadenceChart, pts("cadence"), "#bf5af2", { tension: .3, borderWidth: 1.5 })], { x: elapsedAxis, tooltipTitle: it => mss(it[0].parsed.x) });
  if (ser.temp) timeChart("sheet", $("a-temp"), [lineDs(T.tempChart, pts("temp"), "#64d2ff", { tension: .3, borderWidth: 1.5 })], { x: elapsedAxis, tooltipTitle: it => mss(it[0].parsed.x) });
}

// ---- navigation ------------------------------------------------------------------------------
const loaded = {};
function setTab(name) {
  tab = name;
  document.querySelectorAll(".page").forEach(p => p.classList.toggle("on", p.id === `p-${name}`));
  document.querySelectorAll(".tabbar a").forEach(a => a.classList.toggle("on", a.dataset.tab === name));
  const i = PAGES.indexOf(name);
  $("pill").style.transform = `translateX(${(LANG === "he" ? -1 : 1) * i * 100}%)`;
  $("topbar-title").textContent = T[name === "activities" ? "acts" : name];
  if (!loaded[name]) {
    loaded[name] = true;
    ({ today: renderToday, sleep: () => renderSleep(), activities: renderActivities, trends: renderTrends })[name]().catch(err => { loaded[name] = false; console.error(err); });
  }
}
function route() {
  const h = (location.hash || "#today").slice(1), parts = h.split("/");
  if (parts[0] === "m" || parts[0] === "a") {
    if (!loaded[tab]) setTab(tab);
    (parts[0] === "m" ? openMetric(parts[1], parts[2]) : openActivity(+parts[1])).catch(console.error);
    return;
  }
  hideSheet();
  const name = PAGES.includes(parts[0]) ? parts[0] : "today";
  if (name !== tab || !loaded[name]) { setTab(name); window.scrollTo(0, 0); }
}
addEventListener("hashchange", route);
document.addEventListener("click", e => {
  const a = e.target.closest("a[href^='#']");
  if (!a) return;
  const h = a.getAttribute("href");
  if (h.startsWith("#m/") || h.startsWith("#a/")) { e.preventDefault(); history.pushState({ inApp: true }, "", h); route(); }
});
addEventListener("popstate", route);
addEventListener("scroll", () => $("topbar").classList.toggle("on", window.scrollY > 46), { passive: true });

function refreshAll() {
  cache.clear();
  for (const k in loaded) delete loaded[k];
  setTab(tab);
}
let lastLoad = Date.now();
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && Date.now() - lastLoad > 60000) { lastLoad = Date.now(); refreshAll(); }
});

// ---- sync ------------------------------------------------------------------------------------
const pause = ms => new Promise(r => setTimeout(r, ms));
const runStart = st => st.last_run && st.last_run.started_at;
async function waitForSync(before) {
  $("syncbtn").classList.add("spin");
  let st;
  for (let i = 0; i < 200; i++) {
    await pause(2500);
    st = await (await fetch("/api/status")).json();
    if (!st.running && (before === undefined || runStart(st) !== before)) break;
  }
  $("syncbtn").classList.remove("spin");
  const status = st.last_run && st.last_run.status;
  toast(status === "ok" ? T.syncDone : status === "unchanged" ? T.noNew(st.last_watch_sync ? st.last_watch_sync.slice(11, 16) : "?") : T.lastRun(status || "?"));
  refreshAll();
}
async function sync() {
  if ($("syncbtn").classList.contains("spin")) return;
  const before = runStart(await (await fetch("/api/status")).json());
  const r = await (await fetch("/api/sync", { method: "POST", headers: { "X-Garmin-Health": "1" } })).json();
  if (r.started) return waitForSync(before);
  if (r.reason === "running") { toast(T.syncRunning); return waitForSync(); }
  toast(r.reason === "recent" ? T.syncRecent(Math.ceil(r.retry_after / 60)) : r.reason === "blocked" ? T.syncBlocked : r.reason);
}
$("syncbtn").addEventListener("click", sync);

loadSummary().catch(console.error).finally(route);
