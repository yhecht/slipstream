/**
 * Slipstream - remote MCP connector (Cloudflare Worker).
 *
 * Serves your Garmin training data (read live from your private data repo) to
 * Claude and ChatGPT as a custom connector - so you can ask about it from the
 * phone apps, web, and agent surfaces.
 *
 * Reachable only at /<MCP_SECRET>/mcp (an unguessable path). Summary data only;
 * no GPS / home-location is exposed.
 *
 * Config (set as Worker secrets by the installer):
 *   DATA_REPO     e.g. "you/slipstream" - repo holding data/activities.csv
 *   GITHUB_TOKEN  read-only, contents scope on DATA_REPO
 *   MCP_SECRET    random path segment gating access
 */
import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const CSV_PATH = "data/activities.csv";
const CACHE_TTL_MS = 5 * 60 * 1000;

interface Activity {
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

// --------------------------------------------------------------------------
// CSV + parsing
// --------------------------------------------------------------------------
function parseCsvLine(line: string): string[] {
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

function parseDate(s: string): Date | null {
  if (!s) return null;
  const d = new Date(s.replace(" ", "T") + "Z"); // writer emits UTC "YYYY-MM-DD HH:MM:SS"
  return isNaN(d.getTime()) ? null : d;
}

function parseCsv(text: string): Activity[] {
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

// --------------------------------------------------------------------------
// helpers
// --------------------------------------------------------------------------
function fmtDuration(sec?: number): string | undefined {
  if (sec == null) return undefined;
  const s = Math.round(sec);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}`
    : `${m}:${String(ss).padStart(2, "0")}`;
}

function filterActs(acts: Activity[], o: {
  sport_type?: string; start_date?: string; end_date?: string; name_contains?: string;
}): Activity[] {
  let out = acts;
  if (o.sport_type) { const s = o.sport_type.toLowerCase(); out = out.filter((a) => a.type.toLowerCase() === s); }
  if (o.name_contains) { const q = o.name_contains.toLowerCase(); out = out.filter((a) => a.name.toLowerCase().includes(q)); }
  if (o.start_date) { const t = new Date(o.start_date + "T00:00:00Z").getTime(); out = out.filter((a) => a.date && a.date.getTime() >= t); }
  if (o.end_date) { const t = new Date(o.end_date + "T23:59:59Z").getTime(); out = out.filter((a) => a.date && a.date.getTime() <= t); }
  return out;
}

function summarize(acts: Activity[]) {
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

function toSummary(a: Activity) {
  const pace = a.distanceKm && a.movingS && a.distanceKm > 0
    ? fmtDuration(a.movingS / a.distanceKm) + "/km" : undefined;
  return {
    id: a.id, date: a.date ? a.date.toISOString().slice(0, 10) : null, name: a.name,
    type: a.type, distance_km: a.distanceKm ?? null, moving_time: fmtDuration(a.movingS) ?? null,
    pace: pace ?? null, avg_hr: a.avgHr ?? null, elevation_gain_m: a.elevGain ?? null,
  };
}

function bucketKey(a: Activity, by: string): string | null {
  if (by === "sport") return a.type || "Unknown";
  if (!a.date) return null;
  const y = a.date.getUTCFullYear(), m = a.date.getUTCMonth() + 1;
  if (by === "year") return `${y}`;
  if (by === "month") return `${y}-${String(m).padStart(2, "0")}`;
  return null;
}

// --------------------------------------------------------------------------
// MCP agent
// --------------------------------------------------------------------------
export class FitnessMCP extends McpAgent<Env> {
  server = new McpServer({ name: "slipstream-fitness", version: "1.0.0" });
  private cache?: { at: number; data: Activity[] };

  async getActivities(): Promise<Activity[]> {
    if (this.cache && Date.now() - this.cache.at < CACHE_TTL_MS) return this.cache.data;
    const res = await fetch(
      `https://api.github.com/repos/${this.env.DATA_REPO}/contents/${CSV_PATH}?ref=main`,
      { headers: {
        Authorization: `Bearer ${this.env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github.raw",
        "User-Agent": "slipstream-mcp",
      } },
    );
    if (res.status === 404) return []; // no data yet - first fetch hasn't run
    if (!res.ok) throw new Error(`Could not read fitness data (GitHub ${res.status}).`);
    const data = parseCsv(await res.text());
    this.cache = { at: Date.now(), data };
    return data;
  }

  private text(obj: unknown) {
    return { content: [{ type: "text" as const, text: JSON.stringify(obj, null, 2) }] };
  }

  async init() {
    const dateRange = z.string().describe("YYYY-MM-DD").optional();
    const sport = z.string().describe('e.g. "Run", "Ride", "Swim", "Yoga"').optional();

    this.server.registerTool("data_status", {
      description: "Check the fitness data is connected; returns count, date range, sources.",
      inputSchema: {},
    }, async () => {
      const a = await this.getActivities();
      const dates = a.map((x) => x.date).filter((d): d is Date => !!d).map((d) => d.getTime());
      const srcs: Record<string, number> = {};
      a.forEach((x) => { srcs[x.source] = (srcs[x.source] ?? 0) + 1; });
      return this.text({
        connected: true, count: a.length,
        earliest: dates.length ? new Date(Math.min(...dates)).toISOString().slice(0, 10) : null,
        latest: dates.length ? new Date(Math.max(...dates)).toISOString().slice(0, 10) : null,
        by_source: srcs,
      });
    });

    this.server.registerTool("list_activities", {
      description: "List activities, newest first. Filter by sport/date/name; sort and limit.",
      inputSchema: {
        sport_type: sport, start_date: dateRange, end_date: dateRange,
        name_contains: z.string().optional(),
        limit: z.number().int().min(1).max(200).default(20),
        sort: z.enum(["date_desc", "date_asc", "distance_desc", "distance_asc"]).default("date_desc"),
      },
    }, async (args) => {
      let rows = filterActs(await this.getActivities(), args);
      const cmp: Record<string, (a: Activity, b: Activity) => number> = {
        date_desc: (a, b) => (b.date?.getTime() ?? 0) - (a.date?.getTime() ?? 0),
        date_asc: (a, b) => (a.date?.getTime() ?? 0) - (b.date?.getTime() ?? 0),
        distance_desc: (a, b) => (b.distanceKm ?? 0) - (a.distanceKm ?? 0),
        distance_asc: (a, b) => (a.distanceKm ?? 0) - (b.distanceKm ?? 0),
      };
      rows = [...rows].sort(cmp[args.sort]);
      return this.text({ matched: rows.length, showing: Math.min(args.limit, rows.length),
        activities: rows.slice(0, args.limit).map(toSummary) });
    });

    this.server.registerTool("activity_stats", {
      description: "Totals (distance, time, elevation, calories, avg HR). Optionally group_by sport/month/year.",
      inputSchema: {
        sport_type: sport, start_date: dateRange, end_date: dateRange,
        group_by: z.enum(["sport", "month", "year"]).optional(),
      },
    }, async (args) => {
      const rows = filterActs(await this.getActivities(), args);
      const result: Record<string, unknown> = { overall: summarize(rows) };
      if (args.group_by) {
        const buckets: Record<string, Activity[]> = {};
        for (const a of rows) { const k = bucketKey(a, args.group_by); if (k) (buckets[k] ??= []).push(a); }
        const grouped: Record<string, unknown> = {};
        Object.keys(buckets).sort().forEach((k) => { grouped[k] = summarize(buckets[k]); });
        result["by_" + args.group_by] = grouped;
      }
      return this.text(result);
    });

    this.server.registerTool("personal_bests", {
      description: "Activity-level bests: longest distance, longest time, most elevation, fastest pace.",
      inputSchema: { sport_type: sport },
    }, async (args) => {
      const rows = filterActs(await this.getActivities(), args);
      const best = (f: (a: Activity) => number | undefined, desc = true) => {
        const c = rows.filter((a) => f(a) != null);
        if (!c.length) return null;
        c.sort((a, b) => desc ? (f(b)! - f(a)!) : (f(a)! - f(b)!));
        return toSummary(c[0]);
      };
      return this.text({
        longest_distance: best((a) => a.distanceKm),
        longest_moving_time: best((a) => a.movingS),
        most_elevation_gain: best((a) => a.elevGain),
        fastest_avg_pace: best((a) => (a.distanceKm && a.movingS ? a.movingS / a.distanceKm : undefined), false),
      });
    });

    this.server.registerTool("list_sport_types", {
      description: "Distinct activity types with counts.", inputSchema: {},
    }, async () => {
      const counts: Record<string, number> = {};
      for (const a of await this.getActivities()) counts[a.type || "Unknown"] = (counts[a.type || "Unknown"] ?? 0) + 1;
      return this.text(Object.fromEntries(Object.entries(counts).sort((a, b) => b[1] - a[1])));
    });

    this.server.registerTool("search_activities", {
      description: "Free-text search over activity name, type, and source.",
      inputSchema: { query: z.string(), limit: z.number().int().min(1).max(100).default(20) },
    }, async (args) => {
      const q = args.query.toLowerCase();
      const hits = (await this.getActivities()).filter((a) =>
        a.name.toLowerCase().includes(q) || a.type.toLowerCase().includes(q) || a.source.toLowerCase().includes(q));
      hits.sort((a, b) => (b.date?.getTime() ?? 0) - (a.date?.getTime() ?? 0));
      return this.text({ matched: hits.length, activities: hits.slice(0, args.limit).map(toSummary) });
    });
  }
}

// --------------------------------------------------------------------------
// routing - only the unguessable secret path is served
// --------------------------------------------------------------------------
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const secret = env.MCP_SECRET;
    if (secret && (url.pathname === `/${secret}/sse` || url.pathname === `/${secret}/sse/message`)) {
      return FitnessMCP.serveSSE(`/${secret}/sse`, { binding: "MCP_OBJECT" }).fetch(request, env, ctx);
    }
    if (secret && url.pathname === `/${secret}/mcp`) {
      return FitnessMCP.serve(`/${secret}/mcp`, { binding: "MCP_OBJECT" }).fetch(request, env, ctx);
    }
    if (url.pathname === "/") {
      return new Response("Slipstream MCP connector is running. The data endpoint is private.", {
        headers: { "content-type": "text/plain" },
      });
    }
    return new Response("Not found", { status: 404 });
  },
} satisfies ExportedHandler<Env>;
