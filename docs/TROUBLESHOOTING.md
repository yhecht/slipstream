# Troubleshooting

The setup touches several services (Garmin, GitHub, Cloudflare, Claude, ChatGPT),
so this guide is organized by where the problem shows up. Most fixes are one line.
If you only skim one thing: **paste the connector URL, never type it**, and
**enable the connector inside the chat**, not just in settings.

- [Installer and prerequisites](#installer-and-prerequisites)
- [Garmin](#garmin)
- [GitHub and the scheduled refresh](#github-and-the-scheduled-refresh)
- [Cloudflare](#cloudflare)
- [The connector itself](#the-connector-itself)
- [Claude](#claude)
- [ChatGPT](#chatgpt)
- [Data looks wrong](#data-looks-wrong)
- [Things outside this project's control](#things-outside-this-projects-control)

---

## Installer and prerequisites

**"Missing 'gh' / 'node' / 'python3'".**
Install the tool the installer named (it prints the exact command, e.g.
`brew install gh`) and run `./setup.sh` again.

**"This folder isn't a GitHub repo".**
You ran the installer outside your copy. Create your private copy first:
```bash
gh repo create slipstream --template yhecht/slipstream --private --clone
cd slipstream && ./setup.sh
```

**"... is PUBLIC. Your activity data must not be committed to a public repo".**
This is a safety stop. Make your repo private and rerun:
```bash
gh repo edit <you>/slipstream --visibility private
```

**"... is not owned by you".**
Run the installer from your own copy of the repo, not a clone of someone else's.

**`pip install` fails.**
Usually an old Python or no network. You need Python 3.10+ (`python3 --version`).
Delete `.venv` and rerun so it rebuilds cleanly.

---

## Garmin

**It asks for a 2FA / MFA code.**
Expected if your account has two-factor on. Type only the digits Garmin sends at
the `Garmin MFA code:` prompt.

**`429` / "rate limited by Garmin".**
Garmin throttles repeated login attempts by IP. You only need one successful
login (a token is reused afterward). Fastest fix: connect to your phone's
**hotspot** for a fresh IP and rerun. Otherwise wait about 30 minutes and try
once; do not retry rapidly, each attempt resets the cooldown.

**`401` / authentication failed.**
Wrong email or password, or the account is locked. Sign in at garmin.com to
confirm the credentials and clear any security prompt, then rerun.

**Count is 0 / "No activities written".**
Either there are no Garmin activities in the look-back window, or the saved token
expired (tokens last about a year). Re-mint it:
```bash
GH_REPO="<you>/slipstream" ./.venv/bin/python scripts/garmin_login.py
```

**It worked before and suddenly stops logging in.**
The token may have expired (re-mint as above), or Garmin changed their login flow
and the library needs an update (see [Things outside this project's control](#things-outside-this-projects-control)).

---

## GitHub and the scheduled refresh

**No `data/` folder appears after setup.**
On a brand-new repo, Actions can be disabled until you visit the tab once. Open
your repo, go to **Actions**, enable workflows, then:
```bash
gh workflow run refresh.yml
```
Watch it with `gh run watch`.

**The Action runs but fails.**
Open the failed run's logs. The usual causes: the `GARMINTOKENS` secret is
missing or expired (re-mint), or Garmin returned an error that run (it often
succeeds on the next scheduled run).

**The Action can't push the data.**
The workflow needs write access. It already sets `permissions: contents: write`;
if you edited it, restore that. On forks, also check Settings -> Actions ->
"Workflow permissions" allows read and write.

**Will I run out of free Actions minutes?**
No. Private repos get 2,000 free minutes a month; this job uses a couple of
minutes per run, a few times a day. Public repos are unlimited.

---

## Cloudflare

**I don't have a Cloudflare account.**
No problem, it's free. The installer asks and opens the sign-up page for you.
Choose **Continue with GitHub** for the fastest path (no new password), create the
account, verify your email if prompted, then return to the terminal and press
Enter. A brand-new account works right away.

**`You need a workers.dev subdomain` during deploy.**
Cloudflare only assigns your free web address after the Workers section is
touched once. The installer registers it automatically; if that did not work,
open the dashboard -> **Workers & Pages** (or **Compute -> Workers & Pages**)
once, which creates the subdomain, then rerun `./setup.sh`.

**`wrangler login` didn't open a browser.**
It also prints a URL. Copy it into your browser and approve, then rerun.

**Deploy fails right after sign-up.**
Verify your Cloudflare email (check your inbox), then rerun. Most new-account
deploy failures are an unverified email or the missing subdomain above.

**The Worker returns errors at runtime.**
Stream its logs to see why:
```bash
cd worker && npx wrangler tail
```
Then open the connector URL in a chat to trigger a request.

**Free tier limits.**
Cloudflare's free plan allows 100,000 Worker requests a day. A personal connector
uses a tiny fraction of that.

---

## The connector itself

**"Registration with the auth service failed" / it won't connect.**
Almost always a mistyped URL. The URL ends in a long random secret; one wrong
character makes the Worker return 404, which the app reports as an auth error.
Remove the connector and re-add it, and **paste** the URL.

**It connects but says no data / count 0.**
The first data fetch may not have finished. Trigger it (`gh workflow run
refresh.yml`), wait about a minute, then ask again. If it stays empty, your
Garmin token or the `DATA_REPO` / `GITHUB_TOKEN` Worker secret is wrong; rerun
`./setup.sh`.

**The data is stale.**
The Worker caches for about 5 minutes, and data refreshes every 6 hours. For
fresh numbers right now, run `gh workflow run refresh.yml`, wait a minute, then
ask again.

---

## Claude

**The connector doesn't appear on my phone.**
1. **Force-quit and reopen** the app to sync the new connector.
2. In a **new chat**, open the tools/connector control (a `+` or sliders icon by
   the message box) and **turn the connector on** for that chat.
3. Confirm the phone app is signed into the **same account** you added it to.

**Claude says it has no fitness data or makes up numbers.**
The connector is not enabled for that conversation (see the step above). You know
it works when it returns **real** numbers.

**It asks permission every time it uses a tool.**
In Settings -> Connectors -> your connector, set the tools to **Always allow**.

---

## ChatGPT

**I don't see "Developer mode".**
It requires a paid plan (Plus, Pro, Business, Enterprise, or Edu) and is on the
**web** (Settings -> Apps & Connectors -> Advanced). It is a beta, so it may roll
out gradually.

**Adding the connector fails.**
Paste the full URL (do not type it) and set Authentication to **No
authentication**. If it still fails, open the URL in a browser; you should see a
short "connector is running" message, which confirms the Worker is up.

**ChatGPT won't use the connector.**
Make sure the connector is enabled for the conversation, and ask explicitly, for
example "Using Slipstream, ...". Mobile support for developer-mode connectors can
lag the web; if it is missing on your phone, use the web app.

---

## Data looks wrong

**Units.** Distances are kilometers, times in seconds internally (shown as
H:MM:SS), heart rate in bpm, dates in UTC.

**An activity is missing.** By default the pipeline looks back 30 days. Increase
it by editing `DAYS_BACK` in `.github/workflows/refresh.yml`, or run locally with
`--days 90`.

**A sport shows as "Other" or "Workout".** Garmin has many sport keys; common
ones are mapped to tidy families, and anything unmapped falls back to a generic
label. Open an issue with the sport name and it can be added.

**Numbers differ slightly from the Garmin app.** The app sometimes shows
device-corrected or manually edited values; the connector reports what the API
returns.

---

## Things outside this project's control

This project glues together services owned by other companies. When they change,
something here may need an update. None of these are bugs in your setup:

- **Garmin** can change their login or API at any time. The fetch uses the
  community `python-garminconnect` library; if Garmin changes something, update it
  with `pip install -U garminconnect` (or wait for the library to be patched
  upstream). There is no official public Garmin API for individuals.
- **Claude and ChatGPT** evolve their connector UIs and requirements. The exact
  menu names here may drift; if a step looks different, check their current help
  docs. The connector protocol (MCP) itself is stable.
- **Cloudflare** may adjust free-tier limits or Workers behavior over time.
- **This is read-only and personal-use.** It cannot upload, schedule, or modify
  Garmin data, and it is not affiliated with Garmin, Anthropic, or OpenAI.

Still stuck? Open an issue with the exact command and error text. **Redact any
token and your connector URL first.**
