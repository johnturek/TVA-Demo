# Part 2: Build Your First Agent — Hands-On Lab (25 min)

## Objective

Build a working Copilot Studio agent that answers questions about a public website, guided step-by-step.

---

## Step 1: Open Copilot Studio (2 min)

1. Navigate to **[https://gcc.powerva.microsoft.us](https://gcc.powerva.microsoft.us)**
2. Sign in with your **GCC Microsoft 365 account**
3. Verify you see the Copilot Studio home page

> ⚠️ **GCC Note:** Do NOT use `copilotstudio.microsoft.com` — that is the commercial portal. Always use the GCC URL.

---

## Step 2: Create a New Agent (3 min)

1. Click **"+ Create"** from the left navigation (or the home page)
2. Select **"New agent"**
3. You'll see the agent creation dialog. Fill in:

| Field | Value |
|-------|-------|
| **Name** | `Training Demo Agent` |
| **Description** | `A demo agent for the Copilot Studio training session` |
| **Instructions** | `You are a helpful assistant that answers questions about our training program. Be concise and friendly.` |
| **Language** | English |

4. Click **"Create"**

> 💡 **Tip:** The *Instructions* field is essentially the system prompt — it tells the AI how to behave. Keep it clear and specific.

---

## Step 3: Add a Knowledge Source (5 min)

Let's give the agent something to be smart about.

1. In your agent, click **"Knowledge"** in the left panel
2. Click **"+ Add knowledge"**
3. Select **"Public websites"**
4. Enter a URL your organization uses (or for this lab, use a public documentation site):

   ```
   https://learn.microsoft.com/en-us/microsoft-copilot-studio/fundamentals-what-is-copilot-studio
   ```

5. Click **"Add"**
6. Wait for the indexing to complete (this may take 1-2 minutes)

> 📝 **What's Happening:** Copilot Studio crawls the URL, indexes the content, and makes it available for generative answers. When a user asks a question, the AI searches this knowledge and generates a grounded response.

---

## Step 4: Test Your Agent (5 min)

1. Click the **"Test your agent"** button (bottom-left chat panel, or top-right)
2. The test chat panel opens
3. Try these prompts:

   | Prompt | What You Should See |
   |--------|-------------------|
   | `What is Copilot Studio?` | A generative answer sourced from the knowledge URL |
   | `How do I create a topic?` | A grounded answer with relevant information |
   | `Tell me a joke` | The agent should politely decline or provide a generic response (it's scoped to its knowledge) |

4. Notice the **citation links** in the responses — these show where the answer came from

> ✅ **Checkpoint:** You now have a working agent that answers questions using generative AI grounded in real content!

---

## Step 5: Create a Custom Topic (5 min)

Generative answers are great for open-ended Q&A, but sometimes you need a **structured conversation flow**. That's what topics are for.

1. Click **"Topics"** in the left panel
2. Click **"+ Add a topic"** → **"From blank"**
3. Name the topic: `Training Schedule`
4. Add **trigger phrases** (what the user might say):
   - `What's the training schedule?`
   - `When is the next session?`
   - `Show me the agenda`
   - `Training dates`

5. In the topic canvas, add a **Message node**:
   ```
   📅 Our AI Agent Development Training Series has 3 sessions:

   1️⃣ **Copilot Studio** (Today!) — Build your first AI agent
   2️⃣ **Microsoft AI Foundry** — Deploy and evaluate advanced AI models
   3️⃣ **AI Use Case Development** — Hands-on ideation with GitHub Copilot

   Would you like to know more about any session?
   ```

6. Click **"Save"**
7. Go back to the **Test** panel and try: `When is the next training?`

> 💡 **Key Concept:** Topics give you precise control over the conversation. The AI orchestrator decides whether to use a topic (structured) or generative answers (open-ended) based on the user's input.

---

## Step 6: Explore the Agent Settings (5 min)

Take a few minutes to explore these areas:

### AI Settings
- Click **Settings** (gear icon) → **AI capabilities**
- Note the generative AI toggle and content moderation settings

### Channels
- Click **Settings** → **Channels**
- See deployment options: Teams, Web, Custom (Direct Line)

### Analytics
- Click **Analytics** in the left panel
- This is where you'll monitor usage after publishing

> 🎯 **For GCC Users:** The Teams channel is the most common deployment target. The agent appears as a Teams app that users can chat with directly.

---

## Summary

In 25 minutes, you've:

| ✅ Done | What You Learned |
|---------|-----------------|
| Created an agent | How to set up name, description, and instructions (system prompt) |
| Added knowledge | How generative answers are grounded in real content |
| Tested the agent | How to validate behavior in the test panel |
| Created a topic | How structured conversation flows work alongside generative AI |
| Explored settings | Where to find AI config, channels, and analytics |

---

*Next: Part 3 — Connecting to Microsoft AI Foundry →*
