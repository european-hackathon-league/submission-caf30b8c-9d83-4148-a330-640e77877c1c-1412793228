# EHL Munich 2026 Grand Finale — Claude Code & Multi-Agent Rules (Mandatory)

> **CRITICAL HACKATHON MANDATE (TUM.ai EHL Grand Finale, Oct 10–11, 2026):**
> Make effective use of **Entire** (`https://entire.io/`). Every AI coding agent (Claude Code, Antigravity, Codex, Cursor, Gemini CLI) working in this repository **MUST** capture its agent sessions, use Entire's Continuous Memory (Checkpoints, Search, Graph, Brain, and Trails), and ensure every Git commit is linked to session context. **Submissions without Entire checkpoints pushed to `origin` will NOT be accepted, and effective use of Entire is directly scored.**

- **Repository:** `https://github.com/vamshidharre/Tum.ai_GrandFinale.git` (`gh/vamshidharre/Tum.ai_GrandFinale`)
- **Event Guide:** `https://hack.entire.io/ehl-munich-2026/`
- **Entire Docs for LLMs:** `https://docs.entire.io/llms.txt` (MCP: `https://docs.entire.io/mcp`)

---

## 1. Golden Rules for Claude Code & All AI Agents

1. **Never Bypass Entire Git Hooks:**
   - **NEVER** pass `--no-verify` to `git commit` or `git push`. Entire relies on Git hooks to attach agent session transcripts and push checkpoint refs (`[entire] Pushing checkpoint ref(s) to origin...`) on every commit and push.
2. **CLI Source of Truth (`entire agent-help`):**
   - Never guess `entire` flags or subcommands. Always run `entire agent-help` (or `entire agent-help <command>`) to inspect exact, currently-installed flags.
   - You are already inside `gh/vamshidharre/Tum.ai_GrandFinale` (auto-detected from `origin`). Never ask the user for the repo name.
3. **Commit Focused, Atomic Checkpoints Frequently:**
   - How submissions are scored: *"Make effective use of Entire: capture your agent sessions so your repo gets continuous memory and your agents learn from every attempt, fix and decision."*
   - Make frequent, well-scoped Git commits after each meaningful implementation, bug fix, or architectural decision so Entire records a rich trail of **Checkpoints** (`entire checkpoint list`, `entire checkpoint explain HEAD`).
   - Always `git push` after committing so checkpoints sync to `origin`.
4. **Use Continuous Memory Before Re-inventing or Grepping Blindly:**
   - **Before starting a feature or debugging:** Search previous sessions, commits, and decisions so context carries over across agents (e.g., when switching between Antigravity, Claude Code, and Codex):
     ```bash
     entire search "<query>" --json --compact
     entire checkpoint list
     entire checkpoint explain HEAD
     entire why <file>:<line> --json
     ```
   - **Codebase Navigation (`entire-graph`):** When `entire-graph` is available, use `entire graph` / `entire-graph search` before broad `grep` or full-file reads to locate implementations, trace relationships, and evaluate change impact (saves up to 71% token spend; tracked via `entire graph stats --repo .`).
   - **Cross-Agent Memory (`entire-brain`):** When `entire-brain` is available, consult it for prior architectural decisions, rejected approaches, and cross-agent handoffs.
5. **Trails & Agentic Code Review:**
   - Trail runners are configured in `.entire/runners/`.
   - When working with Trails (`entire trail list`, `entire trail create`, `entire trail show`, `entire trail finding`), keep branch commits clean so Entire Runners (risk, confidence, drift, security, review) can score and review changes automatically.
6. **Self-Healing Diagnostics:**
   - If a session or checkpoint does not appear or hooks look out of sync, run:
     ```bash
     entire status
     entire doctor
     ```

---

## 2. Optional Claude Code MCP Integrations

If running inside Claude Code, you can also attach Entire's live documentation MCP server, Brain MCP server, and the Atira Challenge MCP server:
```bash
claude mcp add --transport http entire-docs https://docs.entire.io/mcp
claude mcp add atira -- atira mcp
```
See `AGENTS.md` for the full **Atira: From RFQ to Bid (`rfq`)** challenge rules and fair-play constraints.



<!-- entire-agent:begin -->
Read .entire/agent-guide.md for this repository's workflow, source inspection, and verification guidance.
@.entire/agent-guide.md
<!-- entire-agent:end -->
