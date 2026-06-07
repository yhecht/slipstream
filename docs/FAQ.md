# FAQ

The questions people ask most about Slipstream. For click-by-click setup, see
[CONNECT.md](CONNECT.md); for fixes, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### 1. What is Slipstream, in one sentence?
A small, self-hosted pipeline that pulls your Garmin activities on a schedule and
lets you talk to them in Claude and ChatGPT, for free.

### 2. How is this different from Strava's MCP, and why would I use it?
Strava's official AI connector requires a paid Strava subscription. Slipstream
goes straight to Garmin (where your data is recorded), runs entirely on free
tiers and your own accounts, and is read-only and private. If you wear a Garmin
and do not want to pay, this is the alternative.

### 3. Is it really free?
Yes. Garmin login is free, GitHub Actions is free (2,000 private minutes a month,
this uses a few), and Cloudflare Workers is free (100,000 requests a day, this
uses a tiny fraction). The only paid thing is optional: ChatGPT's developer-mode
connectors need a paid ChatGPT plan. Claude works on the free plan.

### 4. Do I need a Strava account?
No. Slipstream does not use Strava at all.

### 5. What data does the connector expose? Is my location shared?
Only activity **summaries**: date, sport, distance, duration, heart rate,
elevation, calories, and pace. **No GPS coordinates or routes are exposed**, so
the connector can never reveal where you live or train.

### 6. Who can access my data?
Only you. The connector lives at a long, unguessable URL that acts as the key.
Treat that URL like a password and do not share it. There is no shared backend
and no third-party storage.

### 7. Where is my data actually stored?
In your own private GitHub repository, as a small CSV that the scheduled Action
updates. Nothing leaves your accounts.

### 8. Does it store my Garmin password?
No. Login mints a refreshable session token; only that token is stored (as an
encrypted secret). Your password is never saved.

### 9. How fresh is the data?
The scheduled job refreshes every 6 hours. You can also refresh on demand with
`gh workflow run refresh.yml`, or wire a one-tap phone shortcut (see
[PHONE_TRIGGER.md](PHONE_TRIGGER.md)).

### 10. Does it work on my phone?
Yes. Add the connector once on claude.ai and it appears in the Claude iPhone and
Android apps. ChatGPT's developer-mode connectors are currently web-first.

### 11. Does it work with ChatGPT too?
Yes, the same connector URL. ChatGPT needs a **paid plan** and **Developer mode**
enabled (on the web). Two things trip people up: set Authentication to **No
authentication** (it defaults to OAuth, which fails), and after adding it, switch
it on per chat with **`+` -> More -> Slipstream**. Full steps in
[CONNECT.md](CONNECT.md#chatgpt).

### 12. What can I actually ask it?
Anything about your training: weekly mileage, longest ride, pace trends, training
load, "is a 14 km run reasonable today", and much more. See
[PROMPTS.md](PROMPTS.md) for dozens of examples.

### 13. How far back does it see?
The last 30 days by default. Change `DAYS_BACK` in the workflow (or run the
fetcher with `--days 90`) to widen the window.

### 14. Can it change or upload anything to my Garmin?
No. It is strictly read-only. It cannot create, edit, schedule, or delete
activities, and it cannot push workouts to your device.

### 15. Do I need to know how to code?
No. Setup is one command, and the installer walks you through the rest. Being
comfortable opening a terminal and pasting a command helps, but you do not write
any code.

### 16. Which devices and activities are supported?
Anything your Garmin records: runs, rides, swims, hikes, walks, strength, yoga,
and more. It reads from Garmin Connect, so any device that syncs there works.

### 17. Could this get my Garmin account flagged?
It logs in the same way the official Garmin mobile app does and is for personal,
read-only use at low volume, so the risk is low. It does rely on a community
library (there is no official individual Garmin API), so use it for your own data
and do not hammer it.

### 18. Will I hit any usage limits or surprise costs?
Realistically no. Every component is on a generous free tier and this workload is
tiny (a handful of requests, a few minutes of compute per day).

### 19. Can other people use it? Can I share my setup?
The repository is a template: anyone can click "Use this template" (or run the
one-line installer) to stand up **their own** private instance with their own
data. You never share your data or your connector URL.

### 20. How do I update, harden, or remove it?
Update: `git pull` and rerun `./setup.sh` (it resumes). Harden: swap the data
token for a read-only one (README -> Hardening). Remove: delete the Cloudflare
Worker (`cd worker && npx wrangler delete`), remove the connector in your Claude /
ChatGPT settings, and delete or archive the repo.

### 21. I added the connector, but the assistant acts like it isn't there.
Almost always because it is not switched on **for that conversation**. Adding a
connector in settings makes it available; you still enable it per chat. In Claude,
use the `+` / tools control by the message box; in ChatGPT, click `+` -> More ->
Slipstream. Then ask "Using Slipstream, ...". Real numbers mean it is working.

### 22. ChatGPT shows a "DEV" badge and an "elevated risk" warning. Is that bad?
No. The "DEV" badge just means a developer-mode, unverified connector, which every
self-added connector is. The risk warning is generic boilerplate shown for any
custom connector. Slipstream is read-only and exposes only summaries, so it cannot
delete or change anything.

### 23. Do I have to set it up again on my phone or a second device?
No. The connector is tied to your Claude or ChatGPT **account**, so it appears
wherever you sign in (Claude syncs to its phone apps; ChatGPT is web-first today).
You still flip it on per chat. If it has not appeared on a phone yet, force-quit
and reopen the app to sync.

### 24. Is there a step-by-step guide for connecting?
Yes: [CONNECT.md](CONNECT.md) walks through Claude and ChatGPT click by click,
including the parts people miss.

---

Not covered here? Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue.
This project is independent and not affiliated with Garmin, Anthropic, or OpenAI.
