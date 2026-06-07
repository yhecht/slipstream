#!/usr/bin/env python3
"""One-time Garmin login -> mint a refreshable session token (no password stored).

Handles two-factor: if Garmin prompts, paste the code it sends. On success it
sets the GARMINTOKENS secret on your GitHub repo (so the scheduled Action can
fetch your data). The token auto-refreshes (~1 year), so this is the only login.

If you just hit HTTP 429 (rate limited), wait ~30 min OR switch your machine to
your phone's hotspot (a fresh IP) before retrying.
"""

import getpass
import os
import subprocess
import sys

from garminconnect import Garmin
from garminconnect.exceptions import (
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)


def detect_repo() -> str | None:
    if os.environ.get("GH_REPO"):
        return os.environ["GH_REPO"]
    try:
        r = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True, text=True, check=True,
        )
        return r.stdout.strip() or None
    except Exception:
        return None


def main():
    email = input("Garmin email: ").strip()
    password = getpass.getpass("Garmin password: ")

    print("Logging in… (if prompted, enter the MFA code Garmin sends)", file=sys.stderr)
    g = Garmin(email, password, prompt_mfa=lambda: input("Garmin MFA code: ").strip())

    try:
        g.login()
    except GarminConnectTooManyRequestsError:
        sys.exit("\n✗ Garmin rate-limited this IP (429).\n"
                 "  Fastest fix: connect to your phone's hotspot (a fresh IP) and rerun.\n"
                 "  Otherwise wait ~30 min and DON'T retry in between.")
    except GarminConnectAuthenticationError as e:
        sys.exit(f"\n✗ Garmin auth failed: {e}")

    blob = g.client.dumps()  # full session as a JSON string
    print(f"\n✓ Logged in. Session token = {len(blob)} chars.", file=sys.stderr)

    repo = detect_repo()
    if repo:
        try:
            subprocess.run(["gh", "secret", "set", "GARMINTOKENS", "-R", repo],
                           input=blob.encode(), check=True)
            print(f"✓ Set GARMINTOKENS secret on {repo}. Garmin is done.", file=sys.stderr)
            return
        except Exception as exc:  # noqa: BLE001
            print(f"(couldn't auto-set the secret: {exc})", file=sys.stderr)

    out = "garmin_tokens.txt"
    with open(out, "w") as f:
        f.write(blob)
    print(f"\nWrote {out} (gitignored). Set it manually with:\n"
          f"  gh secret set GARMINTOKENS -R <your-repo> < {out}\n"
          f"then delete {out}.", file=sys.stderr)


if __name__ == "__main__":
    main()
