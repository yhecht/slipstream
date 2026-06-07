import { describe, it, expect } from "vitest";
import {
  parseCsv, summarize, filterActs, toSummary, bucketKey, fmtDuration,
} from "../src/lib";

const CSV = [
  "Activity ID,Activity Date,Activity Name,Activity Type,Raw Sport,Distance,Filename,Moving Time,Elapsed Time,Max Heart Rate,Average Heart Rate,Elevation Gain,Average Speed,Average Watts,Calories,Source",
  "garmin-1,2026-06-01 06:30:00,Morning Run,Run,running,10,,3000,3100,180,160,50,3.33,,600,garmin",
  'garmin-2,2026-06-02 07:00:00,"Hill, Repeats",Run,running,8,,2400,2500,185,168,200,3.33,,500,garmin',
  "garmin-3,2026-05-20 08:00:00,Long Ride,Ride,cycling,40,,7200,7300,160,140,500,5.56,200,1200,garmin",
].join("\n");

describe("parseCsv", () => {
  const acts = parseCsv(CSV);
  it("parses every row", () => expect(acts).toHaveLength(3));
  it("handles a quoted field containing a comma", () =>
    expect(acts[1].name).toBe("Hill, Repeats"));
  it("reads numeric and date fields", () => {
    expect(acts[0].distanceKm).toBe(10);
    expect(acts[0].avgHr).toBe(160);
    expect(acts[0].date?.toISOString()).toBe("2026-06-01T06:30:00.000Z");
  });
  it("returns nothing for header-only input", () =>
    expect(parseCsv("a,b,c")).toHaveLength(0));
});

describe("summarize", () => {
  it("totals distance and averages heart rate", () => {
    const s = summarize(parseCsv(CSV));
    expect(s.activities).toBe(3);
    expect(s.total_distance_km).toBe(58);
    expect(s.avg_hr).toBe(156); // (160 + 168 + 140) / 3
  });
});

describe("filterActs", () => {
  const acts = parseCsv(CSV);
  it("filters by sport (case-insensitive)", () =>
    expect(filterActs(acts, { sport_type: "run" })).toHaveLength(2));
  it("filters by start date inclusive", () =>
    expect(filterActs(acts, { start_date: "2026-06-01" })).toHaveLength(2));
  it("filters by name substring", () =>
    expect(filterActs(acts, { name_contains: "hill" })).toHaveLength(1));
});

describe("toSummary", () => {
  it("computes pace per km", () =>
    expect(toSummary(parseCsv(CSV)[0]).pace).toBe("5:00/km")); // 3000s / 10km
});

describe("bucketKey", () => {
  const a = parseCsv(CSV)[0];
  it("buckets by month/year/sport", () => {
    expect(bucketKey(a, "month")).toBe("2026-06");
    expect(bucketKey(a, "year")).toBe("2026");
    expect(bucketKey(a, "sport")).toBe("Run");
  });
});

describe("fmtDuration", () => {
  it("formats with and without hours", () => {
    expect(fmtDuration(3661)).toBe("1:01:01");
    expect(fmtDuration(125)).toBe("2:05");
    expect(fmtDuration(undefined)).toBeUndefined();
  });
});
