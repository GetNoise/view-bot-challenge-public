# AGENTS.md

Instructions for any coding agent working in this repo. The challenge requires Claude Code,
which reads `CLAUDE.md` and sets everything below up on its own. This file exists so that if
another agent (Codex, Cursor, etc.) is also used, its transcripts are archived the same way.

## Chat log archiving

Transcripts of every agent session in this repo are committed to `chat-logs/`
(`chat-logs/claude/` for Claude Code, `chat-logs/codex/` for Codex), each as the raw `.jsonl`
plus a readable `.txt` rendering made by `scripts/format-chat-log.py`. This is part of the
take-home: reviewers read them alongside the code, and a submission without Claude Code
transcripts is not considered.

At the start of your first turn in a fresh clone, run:

    git config core.hooksPath .githooks

That enables `.githooks/pre-commit`, which copies the latest transcripts into `chat-logs/`,
renders the `.txt` files (needs `python3` on the path), and stages them on every commit.
Claude Code does this automatically via a SessionStart hook.

At the end of every task, before your final reply, also run:

    scripts/archive-chat-logs.sh --commit

It is idempotent and commits only when a transcript changed. Never edit, redact, or delete
anything under `chat-logs/` (including the `.txt` files), and never commit transcripts from
other repos.

## Database

`db/view-bot.sqlite` is a plain SQLite file, built from `db/schema.sql` and `db/seed.sql` by
`scripts/build-db.sh`. Do not edit `db/seed.sql` by hand. See `docs/SCHEMA.md` for the type
conventions (ISO 8601 UTC text timestamps, 0/1 booleans).
