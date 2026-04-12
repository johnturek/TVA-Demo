# Facilitator Guide — TVA Workshop
**Date:** April 15, 2026 | **Location:** TVA HQ, Knoxville TN | **Duration:** 6 hours (9:00 AM–4:00 PM)

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
- [ ] Confirm AI Foundry hub is provisioned in the demo tenant
- [ ] Confirm gpt-4o quota is sufficient (recommend 50K TPM minimum for group)
- [ ] Confirm Azure AI Search instance is ready with `tva-knowledge-base` index pre-built
- [ ] Confirm APIM instance `tva-workshop-apim` is provisioned
- [ ] Test one full run-through of all 3 labs end-to-end

### App Registrations
- [ ] Create the `tva-doc-processor` app registration (run `setup-app-registration.ps1`)
- [ ] Verify app registration has correct API permissions: `openid`, `profile`, `User.Read`
- [ ] Test OBO flow with a test account

### Materials
- [ ] Print lab guides (1 per participant)
- [ ] Print exec brief outline (for exec attendees)
- [ ] Prepare USB drives or SharePoint folder with boilerplate code
- [ ] Send pre-read email to participants with prereqs (Docker, Python, VS Code)

### Docker
- [ ] Pull workshop Docker images on your demo machine
- [ ] Verify `docker compose up` starts both containers cleanly
- [ ] Test all API endpoints locally

---

## D-1 Pre-Workshop Checklist (April 14)

### Final Technical Checks
- [ ] Log into all 3 facilitator accounts — confirm no MFA surprises
- [ ] Confirm TVA WiFi/network allows Azure portal access (no proxy blocking)
- [ ] Test Azure portal, Copilot Studio, and AI Foundry from TVA network specifically
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

| Lab | Target | Buffer | If Behind |
|-----|--------|--------|-----------|
| Lab 1 | 90 min | 15 min | Skip Part 4 REST test; foundry-lab exercises 04–06 are stretch goals |
| Lab 2 | 90 min | 15 min | Skip prompt-based YAML section |
| Lab 3 | 90 min | 15 min | deploy.ps1 handles APIM — focus on MCP + OBO concepts |

**Golden rule:** Never cut the end-to-end demo at the end of each lab. That's the "wow moment" that makes the whole lab land.

**Aaron's foundry-lab exercises:** Labs 01–03 fit within Session 1 time. Labs 04 (multi-agent), 05 (RAG), and 06 (Foundry IQ) are excellent post-workshop exercises or can be used if a group finishes early. Each lab has an interactive exercise menu — participants can pick specific exercises to run.

---

## Top 10 Troubleshooting Scenarios

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
**Fix:** Check the `X-Api-Key` header value matches exactly: `workshop-demo-key-2026`. APIM header check is case-sensitive by default unless `ignore-case="true"` is set in policy.

### 9. MCP tools not discovered in Copilot Studio
**Fix:** Copilot Studio requires MCP server to be publicly accessible (not localhost). Use ngrok to expose local port: `ngrok http 8000` → use the ngrok URL in Copilot Studio MCP config.

### 10. Participant's agent gives wrong answers / ignores documents
**Fix:** Generative answers may be defaulting to general knowledge. In the agent **Overview** page, confirm the knowledge source is connected AND select **"Only use selected knowledge sources"** in the knowledge settings. Note: this setting is on the Overview page, not Settings → Generative AI.

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
