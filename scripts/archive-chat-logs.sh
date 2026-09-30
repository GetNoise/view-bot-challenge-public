#!/usr/bin/env bash
# Copy every Claude Code and Codex transcript for this repo into chat-logs/, and
# write a readable .txt rendering next to each .jsonl (scripts/format-chat-log.py).
#
#   scripts/archive-chat-logs.sh            # copy only (used by the git pre-commit hook)
#   scripts/archive-chat-logs.sh --commit   # copy, then commit chat-logs/ (used by Claude hooks)
#
# Also accepts a Claude Code hook payload on stdin ({"transcript_path": ...}) and
# includes that file even if the sweep below somehow misses it.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$REPO_ROOT/chat-logs"
# Sessions to leave out (the Claude sessions that set this up and moved it to SQLite).
SKIP_IDS="262c5094-fdd1-4ef0-9e9e-689359e11356 2f27d382-516b-407a-99cd-ad46b8cb4dce"
FORMATTER="$REPO_ROOT/scripts/format-chat-log.py"

skip() { case " $SKIP_IDS " in *" $1 "*) return 0 ;; esac; return 1; }

# Copy src to dest when it changed, then (re)render dest as dest-with-.txt when the
# .jsonl changed or the .txt is missing. Rendering is best effort: no python3, no .txt.
copy_if_changed() { # src dest
  [ -f "$1" ] || return 0
  txt="${2%.jsonl}.txt"
  if [ ! -f "$2" ] || ! cmp -s "$1" "$2"; then
    cp "$1" "$2"
    rm -f "$txt"
  fi
  if [ ! -f "$txt" ] && command -v python3 >/dev/null 2>&1; then
    python3 "$FORMATTER" "$2" "$txt" 2>/dev/null || rm -f "$txt"
  fi
}

mkdir -p "$LOG_DIR/claude" "$LOG_DIR/codex"

# --- Claude Code: ~/.claude/projects/<repo path with / -> ->/<session>.jsonl
claude_dir="$HOME/.claude/projects/$(printf '%s' "$REPO_ROOT" | sed 's#[/.]#-#g')"
if [ -d "$claude_dir" ]; then
  for f in "$claude_dir"/*.jsonl; do
    [ -f "$f" ] || continue
    id="$(basename "$f" .jsonl)"
    skip "$id" && continue
    copy_if_changed "$f" "$LOG_DIR/claude/$id.jsonl"
  done
fi

# Transcript handed to us by a Claude hook (stdin JSON), in case it lives elsewhere.
if [ ! -t 0 ]; then
  payload="$(cat || true)"
  t="$(printf '%s' "$payload" | sed -n 's/.*"transcript_path":"\([^"]*\)".*/\1/p')"
  if [ -n "$t" ] && [ -f "$t" ]; then
    id="$(basename "$t" .jsonl)"
    skip "$id" || copy_if_changed "$t" "$LOG_DIR/claude/$id.jsonl"
  fi
fi

# --- Codex: threads table in ~/.codex/state_*.sqlite maps cwd -> rollout_path
if command -v sqlite3 >/dev/null 2>&1; then
  for db in "$HOME"/.codex/state_*.sqlite; do
    [ -f "$db" ] || continue
    sqlite3 -readonly "$db" \
      "select rollout_path from threads where cwd = '$REPO_ROOT' or cwd like '$REPO_ROOT/%';" 2>/dev/null |
    while IFS= read -r rp; do
      [ -f "$rp" ] || continue
      id="$(basename "$rp" .jsonl)"
      skip "$id" && continue
      copy_if_changed "$rp" "$LOG_DIR/codex/$id.jsonl"
    done
  done
fi
# Fallback: rollout files whose header names this repo as cwd.
if [ -d "$HOME/.codex/sessions" ]; then
  grep -rl --include='*.jsonl' "\"cwd\":\"$REPO_ROOT" "$HOME/.codex/sessions" 2>/dev/null |
  while IFS= read -r rp; do
    id="$(basename "$rp" .jsonl)"
    skip "$id" && continue
    copy_if_changed "$rp" "$LOG_DIR/codex/$id.jsonl"
  done
fi

# --- Optionally commit just chat-logs/ (leaves any other staged work alone).
if [ "${1:-}" = "--commit" ]; then
  cd "$REPO_ROOT"
  git add -A -- chat-logs
  git diff --cached --quiet -- chat-logs && exit 0
  git commit -q -m "chore: archive chat logs" -- chat-logs
fi
