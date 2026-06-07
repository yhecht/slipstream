#!/usr/bin/env bash
#
# Slipstream installer - sets up the whole thing end to end.
#   Garmin login  ->  GitHub Action (auto-refresh)  ->  Cloudflare Worker
#   ->  a connector URL you paste into Claude and/or ChatGPT.
#
# Run it from YOUR private copy of this repo:   ./setup.sh
#
set -euo pipefail

BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'
RED=$'\033[31m'; CYAN=$'\033[36m'; RESET=$'\033[0m'
say()  { printf "%s\n" "$*"; }
step() { printf "\n${BOLD}${CYAN}==> %s${RESET}\n" "$*"; }
ok()   { printf "${GREEN}✓${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}!${RESET} %s\n" "$*"; }
die()  { printf "${RED}✗ %s${RESET}\n" "$*" >&2; exit 1; }

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

# --------------------------------------------------------------------------
step "1/6  Checking prerequisites"
need() { command -v "$1" >/dev/null 2>&1 || die "Missing '$1'. Install it (e.g. 'brew install $2') and rerun."; }
need python3 python ; need git git ; need curl curl
need node node ; need npm node ; need openssl openssl
command -v gh >/dev/null 2>&1 || die "Missing GitHub CLI 'gh'. Install from https://cli.github.com (e.g. 'brew install gh'), then rerun."
gh auth status >/dev/null 2>&1 || { warn "Not logged into GitHub CLI - starting login…"; gh auth login; }
GH_USER="$(gh api user --jq .login)"
ok "Tools present. GitHub user: ${BOLD}$GH_USER${RESET}"

# --------------------------------------------------------------------------
step "2/6  Detecting your repo"
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
[ -n "$REPO" ] || die "This folder isn't a GitHub repo. On GitHub, click 'Use this template' to make your own PRIVATE copy, clone it, and run ./setup.sh from there."
[ "${REPO%%/*}" = "$GH_USER" ] || warn "$REPO isn't owned by you ($GH_USER) - make sure you're in YOUR copy."
VIS="$(gh repo view "$REPO" --json visibility -q .visibility 2>/dev/null || echo UNKNOWN)"
[ "$VIS" = "PRIVATE" ] || warn "Your repo is $VIS. It will hold your activity data - PRIVATE is strongly recommended (GitHub: Settings → change visibility)."
ok "Repo: ${BOLD}$REPO${RESET}"

# --------------------------------------------------------------------------
step "3/6  Python environment"
[ -d .venv ] || python3 -m venv .venv
$PY -m pip install --quiet --upgrade pip >/dev/null
$PY -m pip install --quiet -r requirements.txt
ok "Python ready."

# --------------------------------------------------------------------------
step "4/6  Garmin login (one time - handles 2FA, no password stored)"
say "${DIM}If Garmin returns 429 (rate limited): switch to your phone's hotspot for a fresh IP, or wait ~30 min, then rerun.${RESET}"
GH_REPO="$REPO" $PY scripts/garmin_login.py
ok "Garmin connected (token stored as the GARMINTOKENS secret)."

step "   Kicking off the first data fetch"
if gh workflow run refresh.yml -R "$REPO" >/dev/null 2>&1; then
  ok "Refresh workflow triggered - your data will land in data/ within ~1 min."
else
  warn "Couldn't start the workflow. Open the repo's Actions tab once to enable Actions, then run:  gh workflow run refresh.yml -R $REPO"
fi

# --------------------------------------------------------------------------
step "5/6  Cloudflare (free, always-on host for the connector)"
say "You'll approve a Cloudflare login in your browser. No account yet? Make a free one (you can use 'Sign in with GitHub'): ${CYAN}https://dash.cloudflare.com/sign-up${RESET}"
say "${DIM}(After signing up, click 'Workers & Pages' once in the dashboard so Cloudflare gives you a web address.)${RESET}"
read -r -p "Press Enter when you're ready to sign in to Cloudflare… " _ || true
( cd worker && npm install --silent )
( cd worker && npx wrangler login )

# Auto-register a workers.dev subdomain via the API (saves a manual dashboard step).
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
        [ "$(printf '%s' "$RES" | jq_py "print(json.load(sys.stdin).get('success'))" 2>/dev/null)" = "True" ] && { SUB="$cand"; ok "Registered workers.dev subdomain: $cand"; break; }
      done
    else ok "workers.dev subdomain: $SUB"; fi
  fi
fi
[ -n "$SUB" ] || warn "Couldn't auto-detect/register a subdomain. If deploy fails, open 'Workers & Pages' in the Cloudflare dashboard once, then rerun."

# Read-only GitHub token so the Worker can read your data repo.
step "   Read-only data token"
say "Create a ${BOLD}read-only${RESET} GitHub token (so the connector can read your data, nothing more):"
say "  1) Open ${CYAN}https://github.com/settings/personal-access-tokens/new${RESET}"
say "  2) Name: ${BOLD}slipstream-read${RESET}   ·   Resource owner: ${BOLD}$GH_USER${RESET}"
say "  3) Repository access → ${BOLD}Only select repositories${RESET} → ${BOLD}$REPO${RESET}"
say "  4) Permissions → Repository → ${BOLD}Contents${RESET} → ${BOLD}Read-only${RESET}"
say "  5) Generate, copy it."
read -r -s -p "Paste the token (hidden): " PAT; echo
[ -n "$PAT" ] || die "No token entered."

# Secrets + deploy.
MCP_SECRET="$(openssl rand -hex 24)"
( cd worker
  printf "%s" "$REPO"       | npx wrangler secret put DATA_REPO >/dev/null
  printf "%s" "$PAT"        | npx wrangler secret put GITHUB_TOKEN >/dev/null
  printf "%s" "$MCP_SECRET" | npx wrangler secret put MCP_SECRET >/dev/null
  npx wrangler types >/dev/null 2>&1 || true
  npx wrangler deploy
)
ok "Worker deployed."

# --------------------------------------------------------------------------
step "6/6  Your connector"
CONNECTOR_URL="https://slipstream-mcp.${SUB:-YOUR-SUBDOMAIN}.workers.dev/${MCP_SECRET}/mcp"

# Quick health check (the protocol handshake; data may still be fetching).
if [ -n "$SUB" ]; then
  if curl -s --retry 8 --retry-delay 2 --retry-all-errors -X POST "$CONNECTOR_URL" \
      -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"setup","version":"1"}}}' \
      | grep -q "slipstream-fitness"; then
    ok "Connector is live and responding."
  else
    warn "Deployed, but the live check didn't confirm yet (often just needs a few seconds)."
  fi
fi

cat <<EOF

${GREEN}${BOLD}Done!${RESET} Your private connector URL (treat it like a password):

  ${CYAN}${CONNECTOR_URL}${RESET}

${BOLD}Add it to Claude${RESET} (claude.ai → it syncs to the phone app):
  Settings → Connectors → ${BOLD}Add custom connector${RESET} → ${BOLD}paste${RESET} the URL (leave OAuth fields blank) → Add → Connect.

${BOLD}Add it to ChatGPT${RESET} (needs Plus/Pro; web):
  Settings → Apps & Connectors → Advanced → enable ${BOLD}Developer mode${RESET} → Create →
  paste the URL → Authentication: ${BOLD}No authentication${RESET} → Create.

${DIM}Tip: PASTE the URL - don't type it (one wrong character and it won't connect).
Then in a new chat: "Using Slipstream, how far did I run this month?"${RESET}
EOF
