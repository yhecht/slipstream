# Architecture

Slipstream has three moving parts, each on a free tier, each owned by you. There
is no shared backend.

```
┌─────────────────┐   schedule + on-demand    ┌──────────────────────────┐
│  GitHub Actions │ ────────────────────────► │  data/activities.csv     │
│  (your repo)    │   python -m pipeline.fetch │  (committed to your repo)│
└────────┬────────┘                            └────────────┬─────────────┘
         │ python-garminconnect                             │ read-only token
         ▼                                                   ▼
┌─────────────────┐                            ┌──────────────────────────┐
│  Garmin Connect │                            │  Cloudflare Worker        │
└─────────────────┘                            │  /<secret>/mcp            │
                                               └────────────┬─────────────┘
                                                            │ MCP (Streamable HTTP)
                                              ┌─────────────┴─────────────┐
                                              ▼                           ▼
                                          Claude                       ChatGPT
```

## 1. Fetch (`pipeline/`)

A scheduled GitHub Action runs `python -m pipeline.fetch`:

- `sources/garmin.py` logs into Garmin Connect using a **saved session token**
  (`GARMINTOKENS`) - no password is stored - and pulls the last N days of
  activities.
- `schema.py` normalizes each activity (sport families, units) into a small
  `Activity` dataclass.
- `writer.py` serializes them to `data/activities.csv` and commits it.

The CSV is the single source of truth. Its columns are stable and self-describing
(`Activity Date`, `Activity Type`, `Distance`, `Moving Time`, `Average Heart
Rate`, …), all in metric, times in seconds, dates in UTC.

> **Why a CSV in a repo, not a database?** Zero infrastructure. The Action is the
> compute, the repo is the storage, and Git gives you a free history of every
> refresh. A new user needs no server and no DB.

## 2. Serve (`worker/`)

A Cloudflare Worker exposes the data over MCP (the open protocol both Claude and
ChatGPT speak). It's built on the `agents` MCP runtime and the official MCP SDK.

- On a tool call it fetches `data/activities.csv` from your private repo using a
  **read-only, single-repo token** (`GITHUB_TOKEN`), caches it briefly, and
  answers in-memory.
- It exposes six read-only tools: `data_status`, `list_activities`,
  `activity_stats`, `personal_bests`, `list_sport_types`, `search_activities`.
- It serves **only** at `/<MCP_SECRET>/mcp` (and `/sse`). Every other path is a
  404, so the data isn't discoverable without the full secret URL.
- It deliberately exposes **summary data only** - no GPS coordinates leave the
  Worker, so the connector URL can never reveal where you live or train.

Config is injected as Worker **secrets** (`DATA_REPO`, `GITHUB_TOKEN`,
`MCP_SECRET`) - nothing sensitive is in the repo.

## 3. Connect

Claude and ChatGPT both accept remote MCP servers over **Streamable HTTP** with
**no-auth** servers, so the same Worker URL works for both. You paste the URL
once per assistant; it then works across web and mobile.

## Security model

| Concern | Mitigation |
|---|---|
| Garmin password | Never stored; a refreshable session token is used instead. |
| Who can read the data | A long random `MCP_SECRET` in the URL path; treat the URL as a credential. |
| Worker's repo access | A read-only, single-repo fine-grained token. |
| Location privacy | GPS/track data is never exposed by the connector. |
| Where data lives | Your own private GitHub repo - no third-party storage. |

## Extending to more sources

The `pipeline/` layer is source-oriented (`sources/garmin.py`). Adding Wahoo,
Strava, or others is a matter of dropping in a new adapter that yields the same
`Activity` objects, plus a de-duplication pass (the same physical workout can
appear in several places). That multi-source design is the natural next step.
