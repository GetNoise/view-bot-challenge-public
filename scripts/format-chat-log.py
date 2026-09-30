#!/usr/bin/env python3
"""Render a Claude Code or Codex transcript (.jsonl) as readable plain text.

    scripts/format-chat-log.py <transcript.jsonl> [out.txt]
    scripts/format-chat-log.py --full <transcript.jsonl> [out.txt]   # no truncation of tool output

With no output path the text goes to stdout. The archive script calls this for every
transcript it copies into chat-logs/, writing <id>.txt next to <id>.jsonl.

The .jsonl is the record; this file is a reading aid. Long tool results are cut to
TOOL_RESULT_LIMIT characters unless --full is given. Only the standard library is used.
"""
import json
import os
import sys
from datetime import datetime, timezone

TOOL_RESULT_LIMIT = 3000  # characters of tool output kept per result
TOOL_INPUT_LIMIT = 6000   # characters of a tool call's input kept (Write, Edit, ...)
RULE = "-" * 78


def clock(ts):
    """'2026-09-29T13:05:07.020Z' -> '13:05:07'; anything else -> ''."""
    if not ts:
        return ""
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000 if ts > 1e11 else ts, timezone.utc).strftime("%H:%M:%S")
        return ts[11:19]
    except Exception:
        return ""


def indent(text, prefix="    "):
    text = "" if text is None else str(text)
    return "\n".join(prefix + line if line else "" for line in text.rstrip("\n").split("\n"))


def cut(text, limit):
    text = "" if text is None else str(text)
    if limit and len(text) > limit:
        omitted = len(text) - limit
        return text[:limit].rstrip() + f"\n[... {omitted:,} more characters, see the .jsonl ...]"
    return text


def block_text(content):
    """Flatten a message content field (string or list of blocks) to plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict):
                if b.get("type") in ("text", "input_text", "output_text") and b.get("text") is not None:
                    parts.append(str(b["text"]))
                elif b.get("type") == "image":
                    parts.append("[image]")
                elif "text" in b:
                    parts.append(str(b["text"]))
        return "\n".join(parts)
    if isinstance(content, dict) and "text" in content:
        return str(content["text"])
    return json.dumps(content, ensure_ascii=False)


def render_tool_input(name, inp):
    """Show the interesting part of a tool call. Bash gets the command; file edits get the diff."""
    if not isinstance(inp, dict):
        return cut(json.dumps(inp, ensure_ascii=False, indent=2), TOOL_INPUT_LIMIT)
    out = []
    if name == "Bash":
        if inp.get("description"):
            out.append(f"# {inp['description']}")
        out.append(str(inp.get("command", "")))
        rest = {k: v for k, v in inp.items() if k not in ("command", "description")}
        if rest:
            out.append(json.dumps(rest, ensure_ascii=False))
        return "\n".join(out)
    if name in ("Edit", "MultiEdit"):
        out.append(f"file: {inp.get('file_path', '')}")
        edits = inp.get("edits") or [inp]
        for e in edits:
            out.append("--- old")
            out.append(str(e.get("old_string", "")))
            out.append("+++ new")
            out.append(str(e.get("new_string", "")))
            if e.get("replace_all"):
                out.append("(replace_all)")
        return cut("\n".join(out), TOOL_INPUT_LIMIT)
    if name == "Write":
        out.append(f"file: {inp.get('file_path', '')}")
        out.append(str(inp.get("content", "")))
        return cut("\n".join(out), TOOL_INPUT_LIMIT)
    if name == "Read":
        s = f"file: {inp.get('file_path', '')}"
        if inp.get("offset") or inp.get("limit"):
            s += f"  (offset={inp.get('offset')}, limit={inp.get('limit')})"
        return s
    if name in ("Grep", "Glob"):
        return json.dumps(inp, ensure_ascii=False)
    if name in ("Agent", "Task"):
        head = {k: v for k, v in inp.items() if k != "prompt"}
        return cut(json.dumps(head, ensure_ascii=False) + "\nprompt:\n" + str(inp.get("prompt", "")), TOOL_INPUT_LIMIT)
    return cut(json.dumps(inp, ensure_ascii=False, indent=2), TOOL_INPUT_LIMIT)


class Writer:
    def __init__(self, full):
        self.lines = []
        self.full = full

    def section(self, title, ts="", body="", tag=""):
        head = title
        if tag:
            head += f"  {tag}"
        if ts:
            head += f"  [{ts}]"
        self.lines.append("")
        self.lines.append(head)
        if body:
            self.lines.append(indent(body))

    def result(self, text):
        return text if self.full else cut(text, TOOL_RESULT_LIMIT)

    def text(self):
        return "\n".join(self.lines).rstrip() + "\n"


# --------------------------------------------------------------------------- Claude Code

def is_noise_user_text(text):
    t = text.lstrip()
    return t.startswith("<system-reminder>") or t.startswith("<local-command-caveat>")


def render_claude(records, w):
    meta = {"session": None, "title": None, "cwd": None, "branch": None, "version": None,
            "first": None, "last": None, "models": set(), "cost": None}
    tool_names = {}  # tool_use_id -> tool name
    body = Writer(w.full)

    for r in records:
        t = r.get("type")
        ts = r.get("timestamp")
        if ts and isinstance(ts, str):
            meta["first"] = meta["first"] or ts
            meta["last"] = ts
        meta["session"] = meta["session"] or r.get("sessionId")
        meta["cwd"] = meta["cwd"] or r.get("cwd")
        meta["branch"] = meta["branch"] or r.get("gitBranch")
        meta["version"] = meta["version"] or r.get("version")

        if t == "ai-title":
            meta["title"] = r.get("aiTitle") or meta["title"]
        elif t == "cost-state":
            meta["cost"] = r
        elif t == "summary":
            meta["title"] = meta["title"] or r.get("summary")

        if t not in ("user", "assistant"):
            continue
        if r.get("isMeta"):
            continue
        msg = r.get("message") or {}
        content = msg.get("content")
        tag = "(subagent)" if r.get("isSidechain") else ""
        when = clock(ts)

        if t == "user":
            if isinstance(content, str):
                if not is_noise_user_text(content):
                    body.section("USER", when, content, tag)
                continue
            if not isinstance(content, list):
                continue
            texts = []
            for b in content:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text":
                    if not is_noise_user_text(b.get("text", "")):
                        texts.append(b.get("text", ""))
                elif bt == "tool_result":
                    name = tool_names.get(b.get("tool_use_id"), "tool")
                    out = block_text(b.get("content"))
                    label = f"RESULT {name}" + ("  (error)" if b.get("is_error") else "")
                    body.section(label, when, body.result(out), tag)
                elif bt == "image":
                    texts.append("[image]")
            if texts:
                body.section("USER", when, "\n".join(texts), tag)

        else:  # assistant
            if msg.get("model") and not str(msg["model"]).startswith("<"):
                meta["models"].add(msg["model"])
            if not isinstance(content, list):
                if content:
                    body.section("ASSISTANT", when, str(content), tag)
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                bt = b.get("type")
                if bt == "text":
                    if b.get("text", "").strip():
                        body.section("ASSISTANT", when, b["text"], tag)
                elif bt == "thinking":
                    if (b.get("thinking") or "").strip():
                        body.section("THINKING", when, b["thinking"], tag)
                elif bt == "redacted_thinking":
                    pass
                elif bt == "tool_use":
                    name = b.get("name", "tool")
                    tool_names[b.get("id")] = name
                    body.section(f"CALL {name}", when, render_tool_input(name, b.get("input")), tag)

    # Header
    w.lines.append(f"Claude Code session {meta['session'] or ''}".rstrip())
    if meta["title"]:
        w.lines.append(f"Title:    {meta['title']}")
    if meta["first"]:
        span = meta["first"][:19].replace("T", " ") + " UTC"
        if meta["last"] and meta["last"] != meta["first"]:
            span += f"  to  {meta['last'][:19].replace('T', ' ')} UTC"
        w.lines.append(f"When:     {span}")
    if meta["cwd"]:
        w.lines.append(f"Where:    {meta['cwd']}" + (f"  (branch {meta['branch']})" if meta["branch"] else ""))
    if meta["models"]:
        w.lines.append(f"Model:    {', '.join(sorted(meta['models']))}")
    if meta["version"]:
        w.lines.append(f"Version:  Claude Code {meta['version']}")
    c = meta["cost"]
    if c and isinstance(c.get("totalCostUSD"), (int, float)):
        w.lines.append(f"Cost:     ${c['totalCostUSD']:.2f}"
                       f"  (+{c.get('totalLinesAdded', 0)} / -{c.get('totalLinesRemoved', 0)} lines)")
    w.lines.append(RULE)
    w.lines.extend(body.lines)


# --------------------------------------------------------------------------- Codex

def is_noise_codex_text(text):
    t = text.lstrip()
    return (t.startswith("<user_instructions>") or t.startswith("<environment_context>")
            or t.startswith("<INSTRUCTIONS>") or t.startswith("# AGENTS.md"))


def render_codex(records, w):
    meta = {"id": None, "cwd": None, "first": None, "last": None, "version": None,
            "model": None, "originator": None}
    body = Writer(w.full)
    call_names = {}
    have_items = any(r.get("type") == "response_item" for r in records)

    for r in records:
        t = r.get("type")
        p = r.get("payload") or {}
        ts = r.get("timestamp")
        if isinstance(ts, str):
            meta["first"] = meta["first"] or ts
            meta["last"] = ts
        when = clock(ts)

        if t == "session_meta":
            meta["id"] = p.get("id") or meta["id"]
            meta["cwd"] = p.get("cwd") or meta["cwd"]
            meta["version"] = p.get("cli_version") or meta["version"]
            meta["originator"] = p.get("originator") or meta["originator"]
            continue
        if t == "turn_context":
            meta["model"] = p.get("model") or meta["model"]
            meta["cwd"] = meta["cwd"] or p.get("cwd")
            continue

        if t == "response_item":
            pt = p.get("type")
            if pt == "message":
                role = p.get("role")
                text = block_text(p.get("content"))
                if role == "user":
                    if text.strip() and not is_noise_codex_text(text):
                        body.section("USER", when, text)
                elif role == "assistant":
                    if text.strip():
                        body.section("ASSISTANT", when, text)
            elif pt == "reasoning":
                text = block_text(p.get("summary")) or block_text(p.get("content"))
                if text.strip():
                    body.section("THINKING", when, text)
            elif pt in ("function_call", "custom_tool_call"):
                name = p.get("name", "tool")
                call_names[p.get("call_id")] = name
                args = p.get("arguments") if pt == "function_call" else p.get("input")
                shown = args
                if isinstance(args, str):
                    try:
                        parsed = json.loads(args)
                        if isinstance(parsed, dict) and "cmd" in parsed:
                            shown = parsed["cmd"] if isinstance(parsed["cmd"], str) else " ".join(map(str, parsed["cmd"]))
                        elif isinstance(parsed, dict) and "command" in parsed:
                            cmd = parsed["command"]
                            shown = cmd if isinstance(cmd, str) else " ".join(map(str, cmd))
                        else:
                            shown = json.dumps(parsed, ensure_ascii=False, indent=2)
                    except Exception:
                        shown = args
                body.section(f"CALL {name}", when, cut(str(shown), TOOL_INPUT_LIMIT))
            elif pt == "local_shell_call":
                action = p.get("action") or {}
                cmd = action.get("command")
                call_names[p.get("call_id")] = "shell"
                body.section("CALL shell", when, " ".join(map(str, cmd)) if isinstance(cmd, list) else str(cmd))
            elif pt in ("function_call_output", "custom_tool_call_output"):
                name = call_names.get(p.get("call_id"), "tool")
                out = p.get("output")
                if isinstance(out, str):
                    try:
                        parsed = json.loads(out)
                        if isinstance(parsed, dict) and "output" in parsed:
                            out = parsed["output"]
                    except Exception:
                        pass
                elif isinstance(out, dict):
                    out = out.get("output") or json.dumps(out, ensure_ascii=False)
                body.section(f"RESULT {name}", when, body.result(block_text(out) if not isinstance(out, str) else out))
            elif pt == "web_search_call":
                body.section("CALL web_search", when, json.dumps(p.get("action", {}), ensure_ascii=False))
            continue

        if t == "event_msg" and not have_items:
            pt = p.get("type")
            if pt == "user_message":
                text = str(p.get("message", ""))
                if text.strip() and not is_noise_codex_text(text):
                    body.section("USER", when, text)
            elif pt == "agent_message":
                body.section("ASSISTANT", when, str(p.get("message", "")))
            elif pt == "agent_reasoning":
                body.section("THINKING", when, str(p.get("text", "")))
            elif pt == "exec_command_begin":
                cmd = p.get("command")
                body.section("CALL shell", when, " ".join(map(str, cmd)) if isinstance(cmd, list) else str(cmd))
            elif pt == "exec_command_end":
                out = p.get("aggregated_output") or (str(p.get("stdout", "")) + str(p.get("stderr", "")))
                body.section(f"RESULT shell (exit {p.get('exit_code')})", when, body.result(out))

    w.lines.append(f"Codex session {meta['id'] or ''}".rstrip())
    if meta["first"]:
        span = meta["first"][:19].replace("T", " ") + " UTC"
        if meta["last"] and meta["last"] != meta["first"]:
            span += f"  to  {meta['last'][:19].replace('T', ' ')} UTC"
        w.lines.append(f"When:     {span}")
    if meta["cwd"]:
        w.lines.append(f"Where:    {meta['cwd']}")
    if meta["model"]:
        w.lines.append(f"Model:    {meta['model']}")
    if meta["version"]:
        w.lines.append(f"Version:  Codex {meta['version']}" + (f" ({meta['originator']})" if meta["originator"] else ""))
    w.lines.append(RULE)
    w.lines.extend(body.lines)


# --------------------------------------------------------------------------- main

def load(path):
    records = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if isinstance(o, dict):
                records.append(o)
    return records


def detect(records):
    for r in records:
        if r.get("type") in ("session_meta", "response_item", "event_msg", "turn_context"):
            return "codex"
        if r.get("sessionId") or r.get("type") in ("user", "assistant", "attachment"):
            return "claude"
    return "claude"


def main(argv):
    full = False
    args = []
    for a in argv:
        if a == "--full":
            full = True
        else:
            args.append(a)
    if not args or len(args) > 2:
        sys.stderr.write(__doc__)
        return 2
    src = args[0]
    records = load(src)
    w = Writer(full)
    if detect(records) == "codex":
        render_codex(records, w)
    else:
        render_claude(records, w)
    text = w.text()
    if len(args) == 2:
        tmp = args[1] + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, args[1])
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
