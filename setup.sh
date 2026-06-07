#!/usr/bin/env bash
#
# Slipstream installer. Sets up the whole thing end to end:
#   Garmin login  ->  GitHub Action (auto-refresh)  ->  Cloudflare Worker
#   ->  a connector URL you paste into Claude and/or ChatGPT.
#
# Run it from YOUR private copy of this repo. Safe to re-run; it resumes.
#
set -euo pipefail

BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'
RED=$'\033[31m'; CYAN=$'\033[36m'; RESET=$'\033[0m'
say()  { printf "%s\n" "$*"; }
step() { printf "\n${BOLD}${CYAN}==> %s${RESET}\n" "$*"; }
ok()   { printf "${GREEN}✓${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}!${RESET} %s\n" "$*"; }
die()  { printf "\n${RED}✗ %s${RESET}\n" "$*" >&2; exit 1; }
open_url() {
  command -v open    >/dev/null 2>&1 && { open "$1"    >/dev/null 2>&1 || true; return; }
  command -v xdg-open >/dev/null 2>&1 && { xdg-open "$1" >/dev/null 2>&1 || true; return; }
}

cd "$(dirname "$0")"
PY=./.venv/bin/python
jq_py() { "$PY" -c "import sys,json;$1"; }

cat <<'BANNER'

  ____  _ _           _
 / ___|| (_)_ __  ___| |_ _ __ ___  __ _ _ __ ___
 \___ \| | | '_ \/ __| __| '__/ _ \/ _` | '_ ` _ \
  ___) | | | |_) \__ \ |_| | |  __/ (_| | | | | | |
 |____/|_|_| .__/|___/\__|_|  \___|\__,_|_| |_| |_|
           |_|     Garmin -> Claude & ChatGPT, self-hosted & free
BANNER
say "${DIM}This takes ~10 min. You'll need: a Garmin account, a (free) Cloudflare"
say "account, and Claude and/or ChatGPT. I'll open browser pages when needed.${RESET}"

# --------------------------------------------------------------------------
step "1/6  Checking prerequisites"
miss=0
check() { command -v "$1" >/dev/null 2>&1 || { warn "Missing '$1' - install with: ${BOLD}$2${RESET}"; miss=1; }; }
check python3 "brew install python    (or python.org)"
check git     "brew install git"
check curl    "brew install curl"
check node    "brew install node      (or nodejs.org)"
check npm     "brew install node"
check openssl "brew install openssl"
check gh      "brew install gh        (GitHub CLI: cli.github.com)"
[ "$miss" = "0" ] || die "Install the tool(s) above, then run ./setup.sh again."
gh auth status >/dev/null 2>&1 || { warn "Let's log in to GitHub first…"; gh auth login; }
GH_USER="$(gh api user --jq .login)"
ok "All tools present. GitHub user: ${BOLD}$GH_USER${RESET}"

# --------------------------------------------------------------------------
step "2/6  Checking your repo"
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
[ -n "$REPO" ] || die "This folder isn't a GitHub repo. Create your private copy first:
    ${BOLD}gh repo create slipstream --template ${GH_USER}/slipstream --private --clone${RESET}
  (or click 'Use this template' on GitHub), then run ./setup.sh from inside it."
[ "${REPO%%/*}" = "$GH_USER" ] || die "$REPO is not owned by you ($GH_USER). Run this from YOUR copy of the repo."
VIS="$(gh repo view "$REPO" --json visibility -q .visibility 2>/dev/null || echo UNKNOWN)"
[ "$VIS" = "PRIVATE" ] || die "$REPO is ${VIS}. Your activity data must NOT be committed to a public repo.
  Make it private, then rerun:   ${BOLD}gh repo edit $REPO --visibility private${RESET}"
ok "Repo: ${BOLD}$REPO${RESET} (private)"

# --------------------------------------------------------------------------
step "3/6  Python environment"
if [ -d .venv ]; then ok "Already set up."; else
  python3 -m venv .venv
  $PY -m pip install --quiet --upgrade pip >/dev/null
  $PY -m pip install --quiet -r requirements.txt
  ok "Installed."
fi

# --------------------------------------------------------------------------
step "4/6  Garmin"
if gh secret list -R "$REPO" 2>/dev/null | grep -q '^GARMINTOKENS'; then
  ok "Already connected (GARMINTOKENS secret exists). Skipping login."
else
  say "One-time login. Handles 2FA; your password is never stored."
  say "${DIM}If Garmin says 429 (rate limited): connect to your phone's hotspot for a fresh IP, or wait ~30 min, then rerun ./setup.sh.${RESET}"
  GH_REPO="$REPO" $PY scripts/garmin_login.py
  ok "Garmin connected."
fi
gh workflow run refresh.yml -R "$REPO" >/dev/null 2>&1 \
  && ok "Triggered a data refresh (lands in data/ within ~1 min)." \
  || warn "Open the repo's Actions tab once to enable Actions, then: gh workflow run refresh.yml"

# --------------------------------------------------------------------------
step "5/6  Cloudflare (free host - where your connector lives)"
( cd worker && npm install --silent )
if ( cd worker && npx wrangler whoami >/dev/null 2>&1 ); then
  ok "Already signed in to Cloudflare."
else
  read -r -p "Do you already have a Cloudflare account? [y/N] " HAVE_CF || HAVE_CF=""
  if [ "$HAVE_CF" != "y" ] && [ "$HAVE_CF" != "Y" ]; then
    say "No problem - it's free and takes about a minute. Opening the sign-up page now."
    say "${BOLD}Tip: click 'Continue with GitHub'${RESET} - fastest, and no new password."
    open_url "https://dash.cloudflare.com/sign-up"
    say "  ${CYAN}https://dash.cloudflare.com/sign-up${RESET}"
    say "Create the account, ${BOLD}verify your email if it asks${RESET}, then come back here."
    read -r -p "Press Enter once your Cloudflare account is ready… " _ || true
  fi
  say "Now I'll connect to Cloudflare - a browser window opens; click ${BOLD}Allow${RESET}."
  ( cd worker && npx wrangler login )
fi

# Auto-register a workers.dev subdomain via the API (skips a manual dashboard step).
CF_TOKEN=""
for p in "$HOME/Library/Preferences/.wrangler/config/default.toml" \
         "$HOME/.config/.wrangler/config/default.toml" \
         "$HOME/.wrangler/config/default.toml"; do
  [ -f "$p" ] && { CF_TOKEN="$(grep '^oauth_token' "$p" | sed -E 's/^oauth_token *= *"([^"]*)".*/\1/')"; break; }
done
SUB=""
if [ -n "$CF_TOKEN" ]; then
  ACC="$(curl -s https://api.cloudflare.com/client/v4/accounts -H "Authorization: Bearer $CF_TOKEN" | jq_py "print(json.load(sys.stdin)['result'][0]['id'])" 2>/dev/null || true)"
  if [ -n "$ACC" ]; then
    SUB="$(curl -s "https://api.cloudflare.com/client/v4/accounts/$ACC/workers/subdomain" -H "Authorization: Bearer $CF_TOKEN" | jq_py "print((json.load(sys.stdin).get('result') or {}).get('subdomain') or '')" 2>/dev/null || true)"
    if [ -z "$SUB" ]; then
      for cand in "$GH_USER" "${GH_USER}-dev" "${GH_USER}-$RANDOM"; do
        RES="$(curl -s -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACC/workers/subdomain" -H "Authorization: Bearer $CF_TOKEN" -H 'Content-Type: application/json' -d "{\"subdomain\":\"$cand\"}")"
        [ "$(printf '%s' "$RES" | jq_py "print(json.load(sys.stdin).get('success'))" 2>/dev/null)" = "True" ] && { SUB="$cand"; ok "Registered web address: ${cand}.workers.dev"; break; }
      done
    else ok "Your web address: ${SUB}.workers.dev"; fi
  fi
fi
[ -n "$SUB" ] || warn "Couldn't auto-register your web address. If deploy fails, open 'Workers & Pages' in the Cloudflare dashboard once, then rerun."

# Data-read token + connector secret. We reuse your GitHub login for the data
# read (easiest). Advanced/security: swap GITHUB_TOKEN for a read-only
# fine-grained PAT later (see README).
SECRET_FILE=".mcp_secret"
if [ -f "$SECRET_FILE" ]; then MCP_SECRET="$(cat "$SECRET_FILE")"; else MCP_SECRET="$(openssl rand -hex 24)"; printf "%s" "$MCP_SECRET" > "$SECRET_FILE"; fi
( cd worker
  printf "%s" "$REPO"           | npx wrangler secret put DATA_REPO   >/dev/null
  printf "%s" "$(gh auth token)" | npx wrangler secret put GITHUB_TOKEN >/dev/null
  printf "%s" "$MCP_SECRET"     | npx wrangler secret put MCP_SECRET  >/dev/null
  npx wrangler types >/dev/null 2>&1 || true
  npx wrangler deploy
)
ok "Worker deployed."

# --------------------------------------------------------------------------
step "6/6  Connect it to Claude / ChatGPT"
CONNECTOR_URL="https://slipstream-mcp.${SUB:-YOUR-SUBDOMAIN}.workers.dev/${MCP_SECRET}/mcp"

if [ -n "$SUB" ]; then
  curl -s --retry 8 --retry-delay 2 --retry-all-errors -X POST "$CONNECTOR_URL" \
      -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"setup","version":"1"}}}' \
      | grep -q "slipstream-fitness" && ok "Connector is live and responding." \
      || warn "Deployed; the live check didn't confirm yet (usually just needs a few seconds)."
fi

# Put the URL on the clipboard if we can, and open the Claude connectors page.
command -v pbcopy >/dev/null 2>&1 && printf "%s" "$CONNECTOR_URL" | pbcopy && COPIED=" (copied to your clipboard)" || COPIED=""
open_url "https://claude.ai/settings/connectors"

cat <<EOF

${GREEN}${BOLD}Done!${RESET} Your private connector URL${COPIED} - treat it like a password:

  ${CYAN}${CONNECTOR_URL}${RESET}

${BOLD}Claude${RESET} (page opened in your browser; syncs to the phone app):
  Connectors → Add custom connector → ${BOLD}paste${RESET} the URL (leave OAuth blank) → Add → Connect.

${BOLD}ChatGPT${RESET} (needs Plus/Pro; web):
  Settings → Apps & Connectors → Advanced → enable ${BOLD}Developer mode${RESET} →
  Create → paste the URL → Authentication: ${BOLD}No authentication${RESET} → Create.

${DIM}Paste the URL, don't type it. Then ask: "Using Slipstream, how far did I run this month?"
Re-running ./setup.sh later is safe - it resumes and keeps the same URL.${RESET}
EOF
