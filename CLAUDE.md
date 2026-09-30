# CLAUDE.md

## Chat log archiving

Every agent transcript for this repo (Claude Code and Codex) is committed to `chat-logs/`,
except the two Claude sessions that built this setup
(`262c5094-fdd1-4ef0-9e9e-689359e11356` and `2f27d382-516b-407a-99cd-ad46b8cb4dce`).

Layout:

- `chat-logs/claude/<session-id>.jsonl` from `~/.claude/projects/-Users-stu-dev-view-bot-challenge/`
- `chat-logs/codex/<rollout-id>.jsonl` from the Codex rollout files whose `cwd` is this repo
- Next to every `.jsonl`, a `.txt` rendering of the same transcript made by
  `scripts/format-chat-log.py` (plain Python 3, no dependencies) so reviewers can read it
  without parsing JSON. The `.jsonl` is the record; the `.txt` is regenerated whenever the
  `.jsonl` changes and truncates long tool output.

How it happens (all via `scripts/archive-chat-logs.sh`):

1. **Every commit.** `.githooks/pre-commit` copies the latest transcripts in, renders the
   `.txt` files, and stages them, so any commit by a person, Claude, or Codex carries the
   logs up to that moment. The `SessionStart` hook in `.claude/settings.json` enables it with
   `git config core.hooksPath .githooks`; other agents must run that line themselves (see `AGENTS.md`).
2. **After every Claude response.** The `Stop` and `SessionEnd` hooks in `.claude/settings.json`
   run the script with `--commit`, producing a `chore: archive chat logs` commit when anything changed.

Rules for agents:

- If the hooks are disabled or fail, run `scripts/archive-chat-logs.sh --commit` yourself
  at the end of every task, before your final reply.
- Never edit, redact, or delete files under `chat-logs/`, including the `.txt` renderings.
- Never commit transcripts from other repos.

## Database

The data lives in `db/view-bot.sqlite`, built from `db/schema.sql` and `db/seed.sql` by
`scripts/build-db.sh`. Do not edit `db/seed.sql` by hand. The schema conventions
(ISO 8601 UTC text timestamps, 0/1 booleans) are in `docs/SCHEMA.md`.
