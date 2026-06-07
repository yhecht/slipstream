# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's
**private vulnerability reporting** on this repository (the **Security** tab ->
**Report a vulnerability**). You will get a response as soon as possible.

When reporting, never include a real token or your connector URL.

## Security model

Slipstream is designed for **personal, single-user, read-only** access to your
own training data. Understand these properties before deploying it more widely:

- **What is exposed.** The connector serves activity *summaries* only (sport,
  distance, duration, heart rate, elevation, calories, pace). It does **not**
  expose GPS coordinates or routes, so it cannot reveal where you live or train.
- **It is read-only.** It cannot create, edit, delete, or upload Garmin data.
- **Connector access control.** The connector is reachable only at an
  unguessable, high-entropy URL path and returns 404 everywhere else. Treat that
  URL as a credential. This is access-by-secret-URL, **not** per-user OAuth.
  See "Known limitations" below.
- **Secrets at rest.** All credentials (Garmin session token, data-read token,
  the URL secret) are stored as **encrypted GitHub Actions and Cloudflare Worker
  secrets**, never in the repository. `.gitignore` blocks local secret files.
- **Garmin password.** Never stored. Login mints a refreshable session token.
- **Data-read token.** For the simplest setup the Worker reads your private data
  repo using your existing GitHub login. For least privilege, swap it for a
  read-only, single-repo fine-grained token (see README -> Hardening).

## Supply chain

- The Garmin fetch uses the community `python-garminconnect` library (there is no
  official individual Garmin API). It is pinned to a compatible range, and
  Dependabot proposes deliberate upgrades.
- Worker dependencies are locked via `package-lock.json`; Python deps are pinned.
- GitHub Actions are referenced by major version and watched by Dependabot.
  Stricter organizations may pin them to commit SHAs.

## Privacy and telemetry

This project sends **no telemetry**. There is no analytics, no phone-home, and no
shared backend. Everything runs in **your own** GitHub, Cloudflare, Garmin, and
assistant accounts. To remove your data, delete the Cloudflare Worker and the
private data repository.

## Known limitations (important for shared or enterprise use)

- **No per-user authentication.** Access is gated by the secret URL, not OAuth or
  SSO. For multi-user or organizational deployments, put the Worker behind real
  auth, for example Cloudflare Access or an OAuth provider. The Cloudflare remote
  MCP OAuth template is a good starting point.
- **Unofficial Garmin access.** Because there is no official individual API, an
  upstream change can require a dependency bump. Plan for occasional maintenance.
- **Single tenant.** One deployment serves one person's data.

## Non-affiliation

Slipstream is an independent, open-source project and is not affiliated with or
endorsed by Garmin, Anthropic (Claude), or OpenAI (ChatGPT).
