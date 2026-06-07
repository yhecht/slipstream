# Connecting Slipstream to Claude and ChatGPT

`./setup.sh` does the hard part and hands you a **connector URL** that looks like:

```
https://slipstream-mcp.YOUR-SUBDOMAIN.workers.dev/<long-random-secret>/mcp
```

This page is the click-by-click guide for adding that URL to Claude and to
ChatGPT. You only do this once per assistant.

> **One golden rule: paste the URL, never type it.** It ends in a long random
> secret that is the only key to your data. A single wrong character makes it
> fail to connect. The installer copies it to your clipboard; it is also saved
> in `.connector_url` inside your repo folder if you need it again.

> **Labels may differ.** Claude and ChatGPT localize their menus and tweak the
> wording over time. If your app says something slightly different, match the
> closest equivalent. The flow does not change.

---

## Claude

Works on the **free** plan. Add it once on the web and it syncs to the Claude
phone apps on the same account.

1. Open <https://claude.ai/settings/connectors> (Settings, then **Connectors**).
2. Click **Add custom connector**.
3. **Paste** your connector URL into the URL field. Leave the optional OAuth
   Client ID and Client Secret fields **blank**.
4. Click **Add**, then **Connect**.
5. Turn it on in a chat: start a **new chat**, click the tools control (a `+` or
   sliders icon next to the message box), and **enable Slipstream** for that chat.
6. Ask it something real, for example:
   > Using Slipstream, how far did I run this month?

   You will know it works when it returns **actual numbers** from your training.

### On your phone (Claude app)

1. Make sure the app is signed in to the **same account** you used above.
2. If the connector is not there yet, **force-quit and reopen** the app so it
   syncs.
3. In a new chat, open the same tools control and **enable Slipstream** for the
   chat. Per-chat enabling is required on mobile too.

### Optional: stop the per-tool permission prompts

In Settings, then Connectors, open your Slipstream connector and set its tools
to **Always allow**. Then it answers without asking each time.

---

## ChatGPT

Needs a **paid plan** (Plus, Pro, Business, Enterprise, or Edu) and is done on
the **web**. Custom connectors live behind **Developer mode**.

### One time: turn on Developer mode

1. Open **Settings**, then **Apps & Connectors**, then **Advanced settings**.
2. Toggle **Developer mode** on. It shows an "elevated risk" note: that warning
   is generic for any custom connector. Slipstream is **read-only** and exposes
   only activity summaries (no GPS, no account access), so there is nothing for
   it to delete or change.

### Add the connector

3. Back on **Apps & Connectors**, click **Create** (it may read "Create app").
4. Fill in the form:
   - **Name:** `Slipstream`
   - **Description:** optional, leave blank or write "My Garmin training data".
   - **Connection / MCP server URL:** keep the **Server URL** option (not Tunnel)
     and **paste** your connector URL.
   - **Authentication:** change the dropdown to **No authentication**. This is
     the single most common mistake: it defaults to **OAuth**, which will fail
     for this connector.
   - Tick the **"I understand and want to continue"** consent box.
5. Click **Create**. ChatGPT contacts the connector to verify it, then shows a
   confirmation dialog: click **Connect**. Leave "reference chats and memories"
   **off** unless you specifically want it.

   A small **DEV** badge on the connector afterward is normal. It just means
   "developer-mode, unverified", which every self-added connector is.

### Use it in a chat (the step people miss)

6. Adding the connector does **not** switch it on automatically. In a chat,
   click **`+`**, then **More**, then select **Slipstream** so it is active for
   that conversation.
7. Ask it something real, for example:
   > Using Slipstream, how many activities are in my training data, and how far
   > did I run in the last 30 days?

   Expect a real answer with your activity count and distance.

> Mobile support for developer-mode connectors lags the web. If Slipstream does
> not appear in the ChatGPT phone app, use it on the web for now.

---

## Quick comparison

| | Claude | ChatGPT |
|---|---|---|
| Plan needed | Free | Paid (Plus/Pro/Business/Enterprise/Edu) |
| Where you add it | Settings, then Connectors | Settings, then Apps & Connectors, then Developer mode |
| Authentication setting | Leave OAuth fields blank | Choose **No authentication** |
| Phone apps | Yes (sync from web) | Web-first today |
| Enable per chat? | Yes | Yes |

---

## It still will not connect?

- Re-read the golden rule: **paste**, do not type, the URL.
- Open the base URL (everything up to and including `.workers.dev`, then `/`) in
  a browser. You should see a short "connector is running" message, which proves
  the Worker is live and the problem is in the connector setup, not the deploy.
- Full per-assistant fixes are in
  [TROUBLESHOOTING.md](TROUBLESHOOTING.md#claude) (Claude and ChatGPT sections).

Slipstream is an independent project and is not affiliated with Garmin,
Anthropic, or OpenAI.
