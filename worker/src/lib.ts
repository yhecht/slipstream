/**
 * Pure data helpers (CSV parsing, filtering, and stats). Kept separate from the
 * MCP wiring in index.ts so they can be unit-tested without a Worker runtime.
 */

export interface Activity {
  id: string;
  date: Date | null;
  name: string;
  type: string;
  distanceKm?: number;
  movingS?: number;
  elapsedS?: number;
  maxHr?: number;
  avgHr?: number;
  elevGain?: number;
  calories?: number;
  source: string;
}

export function parseCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inq = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inq) {
      if (c === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; } else inq = false;
      } else cur += c;
    } else if (c === ",") { out.push(cur); cur = ""; }
    else if (c === '"') inq = true;
    else cur += c;
  }
  out.push(cur);
  return out;
}

export function parseDate(s: string): Date | null {
  if (!s) return null;
  const d = new Date(s.replace(" ", "T") + "Z"); // writer emits UTC "YYYY-MM-DD HH:MM:SS"
  return isNaN(d.getTime()) ? null : d;
}

export function parseCsv(text: string): Activity[] {
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length < 2) return [];
  const header = parseCsvLine(lines[0]);
  const ix = (name: string) => header.indexOf(name);
  const iId = ix("Activity ID"), iDate = ix("Activity Date"), iName = ix("Activity Name"),
    iType = ix("Activity Type"), iDist = ix("Distance"), iMov = ix("Moving Time"),
    iEl = ix("Elapsed Time"), iMax = ix("Max Heart Rate"), iAvg = ix("Average Heart Rate"),
    iElev = ix("Elevation Gain"), iCal = ix("Calories"), iSrc = ix("Source");
  const acts: Activity[] = [];
  for (let r = 1; r < lines.length; r++) {
    const c = parseCsvLine(lines[r]);
    const num = (i: number) => {
      const v = i >= 0 ? c[i] : "";
      if (!v) return undefined;
      const n = parseFloat(v);
      return isNaN(n) ? undefined : n;
    };
    acts.push({
      id: c[iId] ?? "", date: parseDate(c[iDate] ?? ""), name: c[iName] ?? "",
      type: c[iType] ?? "", distanceKm: num(iDist), movingS: num(iMov), elapsedS: num(iEl),
      maxHr: num(iMax), avgHr: num(iAvg), elevGain: num(iElev), calories: num(iCal),
      source: c[iSrc] ?? "garmin",
    });
  }
  return acts;
}

export function fmtDuration(sec?: number): string | undefined {
  if (sec == null) return undefined;
  const s = Math.round(sec);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`
    : `${m}:${String(ss).padStart(2, "0")}`;
}

export function filterActs(acts: Activity[], o: {
  sport_type?: string; start_date?: string; end_date?: string; name_contains?: string;
}): Activity[] {
  let out = acts;
  if (o.sport_type) { const s = o.sport_type.toLowerCase(); out = out.filter((a) => a.type.toLowerCase() === s); }
  if (o.name_contains) { const q = o.name_contains.toLowerCase(); out = out.filter((a) => a.name.toLowerCase().includes(q)); }
  if (o.start_date) { const t = new Date(o.start_date + "T00:00:00Z").getTime(); out = out.filter((a) => a.date && a.date.getTime() >= t); }
  if (o.end_date) { const t = new Date(o.end_date + "T23:59:59Z").getTime(); out = out.filter((a) => a.date && a.date.getTime() <= t); }
  return out;
}

export function summarize(acts: Activity[]) {
  const sum = (f: (a: Activity) => number | undefined) => acts.reduce((t, a) => t + (f(a) ?? 0), 0);
  const hrs = acts.map((a) => a.avgHr).filter((x): x is number => x != null);
  return {
    activities: acts.length,
    total_distance_km: Math.round(sum((a) => a.distanceKm) * 100) / 100,
    total_moving_time: fmtDuration(sum((a) => a.movingS)) ?? "0:00",
    total_elevation_gain_m: Math.round(sum((a) => a.elevGain) * 10) / 10,
    total_calories: Math.round(sum((a) => a.calories)) || null,
    avg_hr: hrs.length ? Math.round((hrs.reduce((t, x) => t + x, 0) / hrs.length) * 10) / 10 : null,
  };
}

export function toSummary(a: Activity) {
  const pace = a.distanceKm && a.movingS && a.distanceKm > 0
    ? fmtDuration(a.movingS / a.distanceKm) + "/km" : undefined;
  return {
    id: a.id, date: a.date ? a.date.toISOString().slice(0, 10) : null, name: a.name,
    type: a.type, distance_km: a.distanceKm ?? null, moving_time: fmtDuration(a.movingS) ?? null,
    pace: pace ?? null, avg_hr: a.avgHr ?? null, elevation_gain_m: a.elevGain ?? null,
  };
}

export function bucketKey(a: Activity, by: string): string | null {
  if (by === "sport") return a.type || "Unknown";
  if (!a.date) return null;
  const y = a.date.getUTCFullYear(), m = a.date.getUTCMonth() + 1;
  if (by === "year") return `${y}`;
  if (by === "month") return `${y}-${String(m).padStart(2, "0")}`;
  return null;
}
