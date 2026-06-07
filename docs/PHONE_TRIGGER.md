# One-tap refresh from your phone

The data refreshes automatically every 6 hours. If you want a **manual refresh**
(e.g. right after a workout, before asking about it), you can trigger the GitHub
Action from your phone - no laptop needed.

## Option A - GitHub mobile app (easiest)

Install the GitHub app → your repo → **Actions** → **Refresh fitness data** →
**Run workflow**. Done.

## Option B - iOS Shortcut (true one-tap)

1. **Create a fine-grained token** for triggering:
   - <https://github.com/settings/personal-access-tokens/new>
   - Repository access → **Only select repositories** → your `slipstream` repo
   - Permissions → Repository → **Actions** → **Read and write**
   - Generate and copy it.

2. **Build the Shortcut** (Shortcuts app → **+**):
   - Add action **Get Contents of URL**
   - URL:
     ```
     https://api.github.com/repos/<you>/slipstream/actions/workflows/refresh.yml/dispatches
     ```
   - Method: **POST**
   - Headers:
     - `Authorization` = `Bearer YOUR_TOKEN`
     - `Accept` = `application/vnd.github+json`
   - Request Body → **JSON**: `{ "ref": "main" }`

3. Name it "Refresh Garmin", and **Add to Home Screen**.

One tap fires the refresh; your data is up to date in about a minute - even with
your computer switched off.

> Keep the token private. If it ever leaks, revoke it on GitHub and make a new one.
