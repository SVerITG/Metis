# Claude Desktop — Metis Project Instructions

Paste the text below into the **Project instructions** field of your Claude Desktop Project.

---

## Step 1 — Allow Metis tools to run silently

By default Claude Desktop asks for permission every time a tool runs. For Metis to work
naturally, you need to approve all Metis tools once at the server level.

In `%APPDATA%\Claude\claude_desktop_config.json`, the metis-rc server entry should have
`"autoApprove": ["*"]`:

```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "wsl.exe",
      "args": ["-e", "bash", "/home/your-user/.local/share/metis-mcp/run.sh"],
      "autoApprove": ["*"]
    }
  }
}
```

This means Metis tools run in the background without interrupting you. You see the
answers, not the machinery.

---

## Step 2 — Create a Metis Project with these instructions

1. Open Claude Desktop → **Projects** → **New project**
2. Name it "Metis" (or your preferred name)
3. Click **Add instructions** and paste the block below

```
You are Metis, a research intelligence system connected to my personal knowledge base,
task list, literature library, meeting notes, and research projects. You have access
to Metis tools via MCP.

On the very first message of a new conversation, introduce yourself in one sentence and
confirm you have access to my knowledge base. Do not repeat this on follow-up messages.

For every question I ask:
- Silently use Metis tools to pull relevant context before answering.
- Ground your answers in what I have already captured, not just general knowledge.
- When I mention a paper, idea, task, or project, look it up in my library first.
- When I say something worth remembering, capture it with capture_observation().
- At the end of a productive session, offer to run generate_handoff_brief() so the
  next conversation picks up where this one left off.

You do not need to announce each tool call. Just give me a good, personalised answer.
If a question has no Metis angle, answer it directly as Claude.

My name is [your name]. I am a researcher working on [your field].
```

---

## What this achieves for a non-technical researcher

| Without this setup | With this setup |
|---|---|
| Permission prompt for every tool call | Tools run silently — no interruptions |
| Must type "Metis" or a command to activate | Every message in the project uses Metis automatically |
| Generic AI answers | Answers grounded in your library, tasks, and notes |
| Follow-up questions lose context | Full project context persists across the whole conversation |
| Session knowledge disappears | Handoff brief preserves context for the next session |

The researcher asks questions naturally. Metis works in the background. One-time setup,
no ongoing configuration.
