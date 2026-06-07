# 🏃 Slipstream

[![CI](https://github.com/yhecht/slipstream/actions/workflows/ci.yml/badge.svg)](https://github.com/yhecht/slipstream/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Chat with your Garmin training data in Claude and ChatGPT - free, self-hosted, and private.**

Slipstream is a small, self-installing pipeline that pulls your Garmin activities
on a schedule and serves them to AI assistants as a custom [MCP](https://modelcontextprotocol.io)
connector. Ask things like *"how far did I run this month?"* or *"given my
recent fitness, is a 14 km run too much today?"* - from your phone, the web, or
anywhere you use Claude or ChatGPT.

> **A free alternative to Strava's paid MCP.** Strava's official AI connector
> requires a paid subscription. If you wear a Garmin and want the same
> conversational access to your own training - without paying - this is for you.
> Your data, your cloud, no middleman.

---

## What you can ask

Once connected, just talk to your data:

- *"How much did I run and cycle in the last 30 days?"*
- *"What's my longest run, and my fastest average pace?"*
- *"Break down my training by sport this month."*
- *"I want to run a bit longer than usual - is 12-14 km reasonable given my recent fitness?"*
- *"Am I training more or less than last month?"*

Want more ideas? [**`docs/PROMPTS.md`**](docs/PROMPTS.md) has dozens of example
prompts and use cases, from race planning and readiness to recovery, heart-rate
and fueling angles, and a "be my coach" mode.

## How it works

```
   Garmin Connect
        │  (python-garminconnect, token auth - no password stored)
        ▼
  GitHub Actions  ──── every 6h + on-demand ────►  data/activities.csv
   (your private repo)                              (committed automatically)
        │
        │  read-only, on demand
        ▼
  Cloudflare Worker  ◄──── MCP (Streamable HTTP) ────  Claude  ·  ChatGPT
   (free, always-on)                                   (phone, web, agents)
```

- **Fetch** - a scheduled GitHub Action pulls your recent activities and commits
  a tidy `data/activities.csv` to *your* private repo. No server to run.
- **Serve** - a tiny Cloudflare Worker (free tier) reads that file on demand and
  exposes it over MCP at an **unguessable URL**. Summary data only - **no GPS or
  home-location is ever exposed**.
- **Ask** - you add the Worker URL as a custom connector in Claude and/or
  ChatGPT. It works everywhere those apps do, including your phone.

Everything runs on free tiers and your own accounts. There is no shared backend.

## Quick start

You'll need (all free): a **Garmin** account, a **GitHub** account, a
**Cloudflare** account (free; the installer walks you through signup if you
don't have one), and **Claude** and/or **ChatGPT**. Plus `python3`,
`node`, `git`, and the [GitHub CLI](https://cli.github.com) (`gh`) on your machine.

1. **Create your private copy and start the installer** - one command (needs the
   [GitHub CLI](https://cli.github.com)):
   ```bash
   gh repo create slipstream --template yhecht/slipstream --private --clone && cd slipstream && ./setup.sh
   ```
   No `gh`? Click **“Use this template”** on GitHub (make it **Private**), clone
   it, then run `./setup.sh`.
2. **Follow the prompts.** The installer handles Garmin login (2FA), the first
   data fetch, and the Cloudflare deploy - opening browser pages when needed -
   then prints (and copies to your clipboard) your **connector URL**. It's safe
   to re-run; it resumes where it left off.
3. **Paste the URL** into Claude and/or ChatGPT (it opens the page and shows the
   exact clicks). Ask it something. Done.

That's it. From then on your data refreshes automatically every few hours.

## Connecting the assistants

The installer prints your URL and these steps, but for reference:

**Claude** (claude.ai - syncs to the mobile app)
> Settings → Connectors → **Add custom connector** → paste the URL (leave the
> OAuth fields blank) → **Add** → **Connect**. Then enable it in your chat.

**ChatGPT** (requires Plus/Pro; on the web)
> Settings → Apps & Connectors → Advanced → enable **Developer mode** →
> **Create** → paste the URL → Authentication: **No authentication** → **Create**.

> **Always _paste_ the URL - never type it.** It ends in a long random secret;
> one wrong character and it won't connect.

## Privacy & security

- **Your data stays in your own private GitHub repo.** There's no shared server.
- **No GPS / home location is exposed** by the connector - only activity
  summaries (distance, duration, heart rate, sport, etc.).
- The connector lives at an **unguessable URL** (a long random path). Treat that
  URL like a password - it's the only key to your data.
- Your Garmin **password is never stored** - login mints a refreshable session
  token that lives only as encrypted secrets.
- For the simplest setup the Worker reads your data repo using your existing
  GitHub login. Want least-privilege instead? Swap it for a read-only token
  (see **Hardening** below).

### Hardening (optional)

Replace the data-read credential with a **read-only, single-repo** token:

1. Create a fine-grained token at <https://github.com/settings/personal-access-tokens/new>
   - Repository access: **Only select repositories** -> your `slipstream` repo
   - Permissions -> Repository -> **Contents** -> **Read-only**
2. Store it on the Worker:
   ```bash
   cd worker && printf "%s" "<your-token>" | npx wrangler secret put GITHUB_TOKEN
   ```

Now, even in a worst case, the connector can only ever *read* your activity data.

## Keeping data fresh

The GitHub Action runs **every 6 hours** automatically. To refresh on demand
(e.g. right after a workout), trigger it from anywhere:

```bash
gh workflow run refresh.yml
```

You can even wire this to a one-tap phone shortcut - see
[`docs/PHONE_TRIGGER.md`](docs/PHONE_TRIGGER.md).

## Troubleshooting and FAQ

Hit a snag? Every common issue across Garmin, GitHub, Cloudflare, Claude, and
ChatGPT (plus things outside this project's control) is covered in
[**`docs/TROUBLESHOOTING.md`**](docs/TROUBLESHOOTING.md). Broader questions
(cost, privacy, how it compares to Strava's MCP, supported devices) are answered
in [**`docs/FAQ.md`**](docs/FAQ.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - how it is built and the data flow
- [Troubleshooting](docs/TROUBLESHOOTING.md) - every common issue, by area
- [FAQ](docs/FAQ.md) - cost, privacy, comparisons, limits
- [Example prompts](docs/PROMPTS.md) - what to ask, by use case
- [Phone trigger](docs/PHONE_TRIGGER.md) - one-tap refresh from your phone
- [Security policy](SECURITY.md) - posture, reporting, and known limitations
- [Contributing](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md)

## How it's built

A deeper tour of the design is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). In short:

| Piece | Tech |
|-------|------|
| Fetch pipeline | Python · `python-garminconnect` |
| Scheduler | GitHub Actions |
| Connector | Cloudflare Workers · `agents` / MCP SDK · TypeScript |
| Protocol | MCP over Streamable HTTP |

## Roadmap

- ✅ **Garmin** - runs, rides, swims, and everything your watch records.
- ⏳ **Wahoo** (bike power) and **Strava** backfill - planned; the architecture
  already supports multiple sources with de-duplication.

## License

[MIT](LICENSE) © Yannique Hecht

---

<sub>Slipstream is an independent, open-source project. "Garmin", "Claude", and
"ChatGPT" are trademarks of their respective owners; this project is not
affiliated with or endorsed by any of them.</sub>
