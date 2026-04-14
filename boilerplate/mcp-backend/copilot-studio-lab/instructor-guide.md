# Instructor Guide — Session 1: Copilot Studio (90 min)

## Before the Session

### Environment Setup (do this 1 day before)
- [ ] Verify GCC Copilot Studio portal access: `gcc.powerva.microsoft.us`
- [ ] Confirm all attendees have Copilot Studio licenses in GCC
- [ ] Pre-create a demo agent with knowledge, a connector action, and a child agent (backup)
- [ ] Verify AI Foundry demo endpoint is working (test with curl/Postman)
- [ ] Prepare a Power Automate flow for the Foundry integration demo (backup)
- [ ] Test screen sharing on your conferencing tool

### Materials Checklist
- [ ] `00-agenda.md` — Print/share the agenda
- [ ] `01-slides-what-is-copilot-studio.md` — Intro presentation
- [ ] `02-lab-build-first-agent.md` — Hands-on lab Part 1 (share with attendees)
- [ ] `02b-slides-three-pillars.md` — Knowledge, Tools & Agents slides
- [ ] `02c-lab-knowledge-tools-agents.md` — Hands-on lab Part 2 (share with attendees)
- [ ] `03-slides-connecting-to-foundry.md` — The GCC Escape Hatch
- [ ] `04-slides-wrapup.md` — Wrap-up and resources

## During the Session

### Part 1: What Is Copilot Studio? (15 min)
- Move quickly through concepts; the audience will learn by doing in Part 2
- Spend extra time on Slide 5 (GCC specifics) — this is highly relevant
- Ask the discussion prompt on Slide 6 to get audience engagement early

### Part 2a: Build Your First Agent (20 min)
- Have attendees follow along step-by-step
- **Common issues:**
  - Wrong portal URL (commercial vs. GCC) — redirect immediately
  - Knowledge source indexing takes too long — have a pre-indexed agent as backup
  - Trigger phrases don't match — explain the AI fuzzy matching
- Walk around (virtually or in person) to help anyone stuck at Step 3 or 5

### Part 2b: Three Pillars Slides (5-8 min)
- Present the Knowledge / Tools / Agents framework before hands-on
- Use the architecture diagrams to ground the concepts
- Emphasize: "Knowledge = what the agent KNOWS, Tools = what it DOES, Agents = who it ASKS"

### Part 2c: Three Pillars Hands-On Lab (17-20 min)
- **Lab A (Knowledge):** If attendees don't have SharePoint access, have them upload a file instead
- **Lab B (Tools):** MSN Weather is the easiest connector for a mixed audience — no auth required
- **Lab C (Child Agent):** This is the most complex step — slow down here
- **Common issues:**
  - Connector auth prompts in GCC — some connectors require admin consent
  - Generative Actions toggle not visible — may require specific license or admin setting
  - Child agent not routing correctly — check the agent description is clear

### Part 3: The GCC Escape Hatch (20 min)
- **Frame it as a story:** "You've built a great agent in GCC. But what happens when you need something GCC doesn't have yet?"
- This is instructor-led demo — attendees watch
- Lean into the "escape hatch" metaphor — GCC is the compliant front door, Commercial AI Foundry is the powerful back room
- Keep the demo focused; don't go too deep into Foundry (that's Session 2)
- Emphasize the *architecture* and *decision framework* over implementation details
- If the live demo fails, walk through the architecture diagrams and explain

### Part 4: Wrap-Up (10 min)
- Collect questions — write them down for Session 2 prep
- Remind about the optional homework
- Share the resource links

## After the Session

- [ ] Send attendees both lab guides (`02-lab-build-first-agent.md` and `02c-lab-knowledge-tools-agents.md`)
- [ ] Send the resource links from `04-slides-wrapup.md`
- [ ] Note any questions you couldn't answer — research for follow-up
- [ ] Collect feedback (simple 3-question survey: What worked? What didn't? What do you want in Session 2?)

## Timing Contingency

| If running long... | Cut or shorten... |
|--------------------|-------------------|
| Part 1 > 15 min | Skip Slide 6 discussion prompt; summarize use cases verbally |
| Part 2a > 20 min | Skip Step 6 (Explore Settings) — attendees can do on their own |
| Part 2c > 20 min | Skip Lab C (Child Agent) — cover verbally with a pre-built demo |
| Part 3 > 20 min | Skip the live demo; use architecture diagrams only |
