# Facilitator Guide — TVA Workshop
**Date:** April 15, 2026 | **Location:** TVA HQ, Knoxville TN | **Duration:** 7 hours onsite (9:00 AM–4:00 PM) | 6 hours content + 1 hour lunch

---

## Session Ownership

| Session | Owner | Content |
|---------|-------|---------|
| Session 0 — Welcome & Intro | Kevin / Wesley / TVA Leader | Welcome, agenda overview |
| Session 1 — Copilot Studio | John | What Is Copilot Studio, Build Your First Agent, Knowledge/Tools/Agents, Connecting to Foundry |
| Lunch | Kevin + TVA Leadership | Frontier AI Discussion |
| Session 2 — AI Foundry | Aaron / JT | Foundry Overview, Labs 01–04 |
| Session 3 — Use Case Development | All | Brainstorm, team breakout, readout |

---

## Full Day Schedule

| Time | Duration | Segment | Lead |
|------|----------|---------|------|
| 9:00–9:15 AM | 15 min | Session 0: Welcome & Intro | Kevin / Wesley / TVA Leader |
| 9:15–9:30 AM | 15 min | What Is Copilot Studio (slides) | John |
| 9:30–9:55 AM | 25 min | Build Your First Agent (lab) | John |
| 9:55–10:05 AM | 10 min | BREAK | — |
| 10:05–10:30 AM | 25 min | Knowledge, Tools & Agents (slides + lab) | John |
| 10:30–10:50 AM | 20 min | Connecting to Foundry (slides + demo) | John |
| 10:50–11:00 AM | 10 min | Session 1 Wrap‑Up + Q&A | John |
| 11:00–11:30 AM | 30 min | (buffer / overflow) | — |
| 11:30 AM–12:30 PM | 60 min | Lunch — Frontier AI Discussion | Kevin + TVA Leadership |
| 12:30–12:45 PM | 15 min | Foundry Overview & Architecture | Aaron / JT |
| 12:45–1:05 PM | 20 min | Lab 01: Prompts & Completions | Aaron / JT |
| 1:05–1:25 PM | 20 min | Lab 02: Responses API | Aaron / JT |
| 1:25–1:35 PM | 10 min | BREAK | — |
| 1:35–1:55 PM | 20 min | Lab 03: Agents | Aaron / JT |
| 1:55–2:15 PM | 20 min | Lab 04: Multi‑Agent | Aaron / JT |
| 2:15–2:30 PM | 15 min | Session 2 Wrap‑Up | Aaron / JT |
| 2:30–3:00 PM | 30 min | TVA Use Case Brainstorm | All |
| 3:00–3:40 PM | 40 min | Team Breakout: Design an Agent | All |
| 3:40–4:00 PM | 20 min | Readout + Next Steps | All |

---

## D-7 Pre-Workshop Checklist (April 8)

### Tenant & Access
- [ ] Confirm all participant emails — send demo tenant invites
- [ ] Verify Azure portal access for each account
- [ ] Confirm Foundry resource is provisioned in the demo tenant (use the **New Foundry** experience, not classic hubs)
- [ ] Confirm gpt-4o quota is sufficient (recommend 50K TPM minimum for group)
- [ ] Confirm Azure AI Search instance is ready with `tva-knowledge-base` index pre-built
- [ ] Confirm APIM instance `tva-workshop-apim` is provisioned
- [ ] Test one full run-through of all 3 labs end-to-end

### Copilot Studio Access (Session 1)
- [ ] Confirm Copilot Studio licenses assigned for all participant accounts
- [ ] Verify all participants can access https://copilotstudio.microsoft.us (GCC portal)
- [ ] Confirm target Power Platform environment is provisioned for attendee accounts
- [ ] Test creating an agent from a participant account — not just facilitator accounts

### GitHub Codespaces Secrets (Required for Turnkey Classroom Setup)
Participants launch a Codespace and get a fully configured environment — no manual credential setup needed. The repo owner must pre-load shared workshop credentials as Codespace secrets **before** the workshop.

1. Go to repo **Settings → Secrets and variables → Codespaces**
2. Add the following secrets (values come from your provisioned Azure resources):

| Secret Name | Where to Get It |
|-------------|----------------|
| `AZURE_AI_PROJECT_ENDPOINT` | Foundry portal → project → Overview |
| `AZURE_OPENAI_ENDPOINT` | Foundry portal → Models + endpoints → gpt-4o |
| `AZURE_OPENAI_KEY` | Same as above → Key |
| `AZURE_OPENAI_DEPLOYMENT` | Usually `gpt-4o` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Same deployment name — used by foundry-lab exercises (Aaron's labs default to `gpt-4.1`; set to match your actual deployment) |
| `FOUNDRY_AGENT_ENDPOINT` | Same as `AZURE_AI_PROJECT_ENDPOINT` |
| `FOUNDRY_AGENT_KEY` | Same as `AZURE_OPENAI_KEY` |

> **Optional secrets** (for Lab 3 / advanced labs): `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `OBO_CLIENT_ID`, `OBO_CLIENT_SECRET`, `OBO_TENANT_ID`, `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_ADMIN_KEY`
>
> **Foundry-lab specific:** Set `DISABLE_CODE_INTERPRETER_LAB=true` if your region does not support container-based Code Interpreter — this skips Lab 03 Exercise 2 instead of failing with a provisioning error.

3. Test it: open a fresh Codespace and verify `.env` is auto-populated (look for "Auto-populated N values from Codespace secrets" in terminal output)

- [ ] Codespace secrets added to repo settings
- [ ] Verified Codespace launches with credentials pre-loaded
- [ ] Codespace link tested: `https://codespaces.new/johnturek/tva-demo?quickstart=1`

### GitHub Access (Required for Codespaces)
- [ ] Confirm all participants have a GitHub account (free tier is fine)
- [ ] Verify repo is public or participants have been granted access
- [ ] Test Codespace launch from a non-facilitator GitHub account
- [ ] Consider pre-building a Codespace to reduce first-launch wait times

### App Registrations
- [ ] Create the `tva-doc-processor` app registration (run `setup-app-registration.ps1`)
- [ ] Verify app registration has correct API permissions: `openid`, `profile`, `User.Read`
- [ ] Grant admin consent for the app registration in Azure portal
- [ ] Add Copilot Studio redirect URL via `add-reply-url.ps1`
- [ ] Assign `MCP.User` app role to all participant accounts via `add-users.ps1`
- [ ] Test OBO flow with a test account

### Materials
- [ ] Prepare printed check-in cards with: Codespace link (QR code), demo tenant credentials, WiFi info
- [ ] Print lab guides (1 per participant) — backup for screen-only workers
- [ ] Print exec brief outline (for exec attendees)
- [ ] Print exec observation sheets (see "Handling the Mixed Audience" section)
- [ ] Send pre-read email to participants with: GitHub account requirement, Codespace link, agenda overview

### Docker
- [ ] Pull workshop Docker images on your demo machine
- [ ] Verify `docker compose up` starts both containers cleanly
- [ ] Test all API endpoints locally

---

## D-1 Pre-Workshop Checklist (April 14)

### Final Technical Checks
- [ ] Log into all 3 facilitator accounts — confirm no MFA surprises
- [ ] Confirm TVA WiFi/network allows Azure portal, Copilot Studio, GitHub, and AI Foundry access (no proxy blocking)
- [ ] Test Azure portal, Copilot Studio, and AI Foundry from TVA network specifically
- [ ] Launch a fresh Codespace from TVA network — verify it builds and credentials load
- [ ] Verify Docker Desktop works on facilitator laptops on TVA network
- [ ] Run `docker compose up` one more time — confirm clean start
- [ ] Test APIM endpoint from TVA network

### Room Setup
- [ ] At least 2 large displays (one for presenter, one for demo)
- [ ] HDMI cables + adapters for Mac/PC
- [ ] Participants seated with power strips accessible
- [ ] WiFi credentials printed and on each table
- [ ] Whiteboard + markers for architecture diagrams
- [ ] Printed materials at each seat

### Comms
- [ ] Slack/Teams channel open with all facilitators for real-time coordination
- [ ] JT's fallback demo tenant credentials accessible offline (in case portal is slow)
- [ ] Have `private.turek.in` portal open as last-resort demo fallback

### Morning Check-In Prep
- [ ] Check-in cards printed (one per participant): Codespace QR code, demo tenant login, WiFi password
- [ ] Assign exec/dev pairing plan — who shadows whom during labs
- [ ] Facilitator run-of-show reviewed: who presents what, who handles roaming support
- [ ] All facilitator laptops have fallback URLs bookmarked and local clone ready

---

## Handling the Mixed Audience

Executives and developers have different needs. Don't ignore either group.

### Executive Track Tips

**At Kickoff:**
- Open with the business problem, not the technology
- Lead with: "By end of day, your team will have a working AI agent that can answer compliance questions in seconds instead of hours"
- Show the ROI slide before any technical content

**During Labs:**
- Assign execs a "shadow" developer partner — they watch and ask questions
- Give execs a printed "exec observation sheet" with questions to think about:
  - "What business process could this replace?"
  - "Who would use this in your organization?"
  - "What data would you feed this?"
- Pull execs out for 10-min "exec breakout" during Lab 2 — discuss deployment strategy, governance, rollout

**At Wrap-up:**
- Recap in business terms: "You built X, it can do Y, it saves Z"
- Give execs a clear "next 3 steps" they can take back to leadership

### Developer Track Tips
- Encourage them to break things — that's how they learn
- Have the boilerplate repo cloned and ready so nobody loses time on setup
- Pair strong devs with others who get stuck

---

## Timing Guidance

> **Note:** The 3 labs (Lab 1–3 in the `workshop/` folder) do not map 1:1 to the 3 sessions. Session 1 uses Lab 2 content (Copilot Studio). Session 2 uses Lab 1 content (Foundry) plus Aaron's foundry-lab exercises. Lab 3 (APIM+MCP) is covered as a demo/walkthrough during "Connecting to Foundry" and as a post-workshop self-guided exercise.

| Session | Scheduled Time | Content Time | Buffer | If Behind |
|---------|---------------|-------------|--------|-----------|
| Session 1: Copilot Studio | 9:15–11:30 AM | 95 min + 10 min break | 30 min overflow | Skip Lab 2 Part 5 (prompt-based YAML) |
| Session 2: AI Foundry | 12:30–2:30 PM | 110 min + 10 min break | None — stay on schedule | foundry-lab exercises 04–07 are stretch goals |
| Session 3: Use Cases | 2:30–4:00 PM | 90 min | Built-in — readout can flex | Shorten brainstorm to 20 min if behind |

**Golden rule:** Never cut the end-to-end demo at the end of each lab. That's the "wow moment" that makes the whole lab land.

**Aaron's foundry-lab exercises:** Labs 01–03 fit within Session 2 time. Labs 04 (multi-agent), 05 (RAG), 06 (Foundry IQ), and 07 (AI Foundry Agent API with OBO auth) are excellent post-workshop exercises or can be used if a group finishes early. Each lab has an interactive exercise menu — participants can pick specific exercises to run.

**Lab 3 (APIM+MCP):** This lab is not a standalone scheduled session. JT demos the deploy/MCP flow during Session 1's "Connecting to Foundry" segment (10:30–10:50 AM). Participants can self-guide through the full Lab 3 post-workshop using the lab guide.

**Aaron's Copilot Studio content:** The submodule also contains a `copilot-studio-lab/` directory with slides, instructor guide, and GCC-specific scripts for Copilot Studio. This content complements Session 1 — facilitators can reference it for additional GCC setup steps or as a standalone self-guided Copilot Studio lab.

**Deploy script tips:** Aaron's `deploy.ps1` supports `-ResourceGroupOverride <name>` to target a pre-existing resource group (useful for locked-down workshop tenants), and foundry-lab's `deploy.ps1` supports `-ExplainOnly` to show what each step does without executing — good for teaching mode.

---

## Top 14 Troubleshooting Scenarios

### 1. Participant can't log into Azure portal
**Fix:** Check they're using the demo tenant account (not their personal/work account). URL: `https://portal.azure.com` → click avatar → Switch directory → select workshop tenant.

### 2. AI Foundry hub not visible
**Fix:** Subscription filter. In portal, click **Subscriptions** filter icon → check "Select all". The workshop subscription may be hidden.

### 3. Vector index stuck in "Running" state
**Fix:** Delete and recreate. First-time storage provisioning can stall. Second attempt succeeds 99% of the time.

### 4. gpt-4o returns 429 Too Many Requests
**Fix:** Workshop quota is shared. Tell participants to stagger their test queries — don't all hit it simultaneously. Add a 5-second wait between retries.

### 5. Copilot Studio agent won't connect to Azure AI Search
**Fix:** The connection requires the search endpoint URL to include `https://` prefix. Also verify the API key has "Query" permissions, not just "Admin".

### 6. HTTP action in Copilot Studio returns empty response
**Fix:** The response parser expects `application/json`. Check the backend returns proper `Content-Type` header. In Docker backend, verify Express is using `res.json()` not `res.send()`.

### 7. Docker containers won't start on TVA network
**Fix:** Corporate proxy may block Docker Hub pulls. Have pre-pulled images on USB drives as backup. Run: `docker load < tva-workshop-images.tar`

### 8. APIM returns 401 on every request
**Fix:** If using the OAuth/OBO flow (Lab 3), verify the JWT audience matches `api://[your-app-id]` and the user has the `MCP.User` app role assigned. If using the API key fallback for quick demos, check the `X-Api-Key` header value matches exactly: `workshop-demo-key-2026` (case-sensitive).

### 9. MCP tools not discovered in Copilot Studio
**Fix:** Copilot Studio requires MCP server to be publicly accessible (not localhost). Use ngrok to expose local port: `ngrok http 8000` → use the ngrok URL in Copilot Studio MCP config. In the production flow, use the APIM endpoint URL from `deploy.ps1` output.

### 10. Participant's agent gives wrong answers / ignores documents
**Fix:** Generative answers may be defaulting to general knowledge. In the agent **Overview** page, confirm the knowledge source is connected AND select **"Only use selected knowledge sources"** in the knowledge settings. Note: this setting is on the Overview page, not Settings → Generative AI.

### 11. Codespace won't start or takes too long
**Fix:** Verify participant is signed into the correct GitHub account (not a work SSO account that blocks Codespaces). Check they haven't exceeded the free tier (60 hrs/month). If Codespace creation is slow, the devcontainer may be building from scratch — consider pre-building a Codespace image. Fallback: use Azure Cloud Shell (Option B in `setup-environment.md`).

### 12. `az login` succeeds but wrong tenant/subscription
**Fix:** After login, run `az account show` to verify the tenant name. If wrong, run `az login --tenant <workshop-tenant-id> --use-device-code`. In Codespaces, participants may default to their personal subscription. Have the workshop tenant ID printed on the check-in card.

### 13. `.env` not populated / wrong deployment name
**Fix:** If Codespace secrets weren't configured, participants must manually fill in `.env`. Run `cp .env.example .env` if the file is missing. The most common mistake is wrong model deployment name — verify `AZURE_OPENAI_DEPLOYMENT` matches the actual deployment name in the Foundry portal. Note: the main workshop labs use `gpt-4o`, but Aaron's foundry-lab exercises default to `gpt-4.1` (see `foundry-lab/example.env`). Make sure `AZURE_OPENAI_DEPLOYMENT_NAME` matches whichever model is deployed in your Foundry resource.

### 14. Copilot Studio license or environment missing
**Fix:** Participant needs a Copilot Studio license assigned in the admin center. If they can access the portal but can't create agents, check they're in the correct Power Platform environment. Have a facilitator create the agent and share it as a fallback.

---

## Fallback Plan

If demo tenant access fails completely:

1. **First fallback:** Use JT's pre-built demo at `https://private.turek.in/demos/tva/` — shows the finished product
2. **Second fallback:** Facilitator live-demos from their own working setup while participants follow along
3. **Third fallback:** Switch to pure presentation mode — show recordings of each lab step

Pre-load fallback URLs on all facilitator laptops before the day.

---

## Post-Workshop
- Send repo link to all participants: https://github.com/johnturek/TVA-Demo
- Send follow-up email within 48 hours with:
  - Recording link (if session recorded)
  - Next steps document
  - Contact for questions (JT)
- Log any issues/feedback in the repo Issues tab for future workshops
