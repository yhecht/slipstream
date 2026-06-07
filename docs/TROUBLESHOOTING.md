# Troubleshooting

The setup touches a few services, so here are the snags people actually hit - 
each with the fix. Most are one-liners.

## Garmin

**It asks for an MFA / 2FA code.**
That's expected if your Garmin account has two-factor on. The login script
prompts `Garmin MFA code:` - paste the 6 digits Garmin emails/texts you and press
Enter. Type **only the digits**.

**`429` / "rate limited by Garmin".**
Garmin throttles repeated login attempts by IP. You only need **one** successful
login (after that, a saved token is reused - no more logins). To get through:
- **Fastest:** connect your computer to your **phone's hotspot** (a fresh IP that
  isn't throttled) and rerun.
- **Otherwise:** wait ~30 minutes and try once. Don't retry rapidly - each
  attempt resets the cooldown.

**`No activities written` / count is 0.**
Either there are no Garmin activities in the last 30 days, or the saved token
expired (they last ~1 year). Re-mint it:
```bash
GH_REPO="<you>/slipstream" ./.venv/bin/python scripts/garmin_login.py
```

## GitHub Actions

**The workflow didn't run / no `data/` appears.**
On a brand-new repo, Actions may be disabled until you visit the tab once. Open
your repo → **Actions** → enable workflows, then:
```bash
gh workflow run refresh.yml
```
Check progress with `gh run watch`.

## Cloudflare

**`You need a workers.dev subdomain` during deploy.**
Cloudflare only assigns your free web address after you open the Workers section
once. The installer tries to register it automatically; if that didn't work, open
the Cloudflare dashboard → **Workers & Pages** (or **Compute → Workers & Pages**)
once - landing there creates the subdomain - then rerun `./setup.sh`.

**`wrangler login` didn't open a browser.**
It prints a URL - copy it into your browser and approve. Then rerun.

## The connector

**"Registration with the auth service failed" / it won't connect.**
99% of the time this is a **mistyped URL**. The URL ends in a long random secret;
a single missing character makes the Worker return 404, which the app reports as
an auth error. Remove the connector and re-add it, and **paste** the URL - don't
type it.

**The connector doesn't appear on my phone.**
1. **Force-quit and reopen** the Claude/ChatGPT app to sync the new connector.
2. In a **new chat**, open the tools/connector control (often a `+` or sliders
   icon by the message box) and **toggle the connector on** for that chat.
3. Make sure the phone app is signed into the **same account** you added the
   connector to.

**Claude says it has no fitness data / makes up numbers.**
The connector isn't enabled for that conversation - see the step above. You'll
know it's working when it returns **real** numbers (run `data_status` mentally:
ask *"is my fitness connector connected?"*).

## Shell gotchas (manual steps)

**`zsh: command not found: …` after pasting a command.**
You probably pasted a multi-line block that included a `#` comment - interactive
zsh tries to run comments. Paste/run **one command at a time**, without the
explanatory comments.

**`no such file or directory: ./.venv/bin/python`.**
You're not in the project folder. `cd` into your cloned `slipstream` directory
first.

---

Still stuck? Open an issue with the exact command and the error text (redact any
token or the connector URL first).
