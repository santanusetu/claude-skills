#!/usr/bin/env python3
"""List recent Claude Code sessions for a project, with enough context to summarise them.

Reads the transcripts Claude Code keeps under ~/.claude/projects/<encoded project path>/
(or $CLAUDE_CONFIG_DIR/projects/), and `ps` to see which sessions are open right now.
Read-only: it never writes, moves or deletes anything, and nothing leaves your machine.

Usage:
  sessions.py [--count 4] [--more 2] [--project DIR] [--include-current] [--json]
"""
import argparse, datetime, glob, json, os, re, subprocess, sys

RECENT_MINUTES = 10  # last message this recently: someone may still be typing in it
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def projects_root():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(base, "projects")


def encode(path):
    """Claude Code names a project's transcript folder after its path, with every
    non-alphanumeric character replaced by '-'."""
    return os.path.join(projects_root(), re.sub(r"[^A-Za-z0-9]", "-", path))


def find_project(start):
    """Nearest folder at or above `start` that has transcripts.

    Claude's shell often drifts into a subfolder (e.g. my-app/src) while the session
    belongs to the folder Claude was launched from, so walk upwards.
    """
    path = os.path.abspath(os.path.expanduser(start))
    while True:
        if glob.glob(os.path.join(encode(path), "*.jsonl")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


RUNTIMES = {"node", "nodejs", "bun", "deno"}


def claude_args(parts):
    """The arguments of a Claude Code process, or None if `parts` is some other program.

    The native installer runs as `claude …`. An npm install runs through a runtime,
    so ps shows `node /…/bin/claude …` or `node /…/@anthropic-ai/claude-code/cli.js …`.
    """
    if not parts:
        return None
    # Case-sensitive on purpose: the CLI is lowercase `claude`, while the Claude desktop
    # app runs as `…/Claude.app/…/Claude` and `Claude Helper`, which are not sessions.
    exe = os.path.basename(parts[0])
    if exe in ("claude", "claude.exe"):
        return parts[1:]
    if exe in RUNTIMES and len(parts) > 1:
        script = parts[1]
        name = os.path.basename(script)
        if name == "claude" or ("claude-code" in script and name.startswith("cli.")):
            return parts[2:]
    return None


def parse_ps(output):
    """Session IDs named on a running Claude Code command line, plus a count of Claude
    processes that name no session (a fresh `claude`, whose ID is not visible)."""
    ids, unnamed = set(), 0
    for line in output.splitlines():
        args = claude_args(line.split())
        if args is None:
            continue
        if {"-p", "--print", "--chrome-native-host"} & set(args):
            continue  # one-shot runs and helpers, not interactive sessions
        found = re.findall(UUID, " ".join(args))
        if found:
            ids.update(found)
        else:
            unnamed += 1
    return ids, unnamed


def open_sessions():
    try:
        out = subprocess.run(["ps", "-axo", "args="], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return set(), None  # no `ps` (e.g. Windows): open status unknown
    return parse_ps(out)


def text_of(msg):
    c = (msg.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return ""


def clean_prompt(t):
    """Return the prompt a person actually typed, or None for harness noise."""
    t = t.strip()
    if not t:
        return None
    m = re.search(r"<command-name>(.*?)</command-name>", t, re.S)
    if m:
        args = re.search(r"<command-args>(.*?)</command-args>", t, re.S)
        return (m.group(1).strip() + " " + (args.group(1).strip() if args else "")).strip()
    if t.startswith("<") or t.startswith("Caveat:") or "[Request interrupted" in t:
        return None
    return t


def parse_ts(ts):
    if not ts:
        return None
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()


def fmt(dt, today):
    if dt is None:
        return "?"
    clock = f"{dt.hour % 12 or 12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"
    return clock if dt.date() == today else f"{dt.strftime('%a')} {dt.day} {dt.strftime('%b')} {clock}"


def one_line(t, n):
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def read_session(path):
    s = {"title": None, "custom": False, "first_ts": None, "last_ts": None,
         "prompts": [], "last_reply": "", "cwd": None}
    with open(path, errors="replace") as fh:
        for line in fh:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            typ = m.get("type")
            if typ == "custom-title" and m.get("customTitle"):
                s["title"], s["custom"] = m["customTitle"], True
            elif typ == "ai-title" and m.get("aiTitle") and not s["custom"]:
                s["title"] = m["aiTitle"]
            if m.get("isSidechain"):
                continue  # subagent traffic, not the conversation the user had
            ts = m.get("timestamp")
            if ts and typ in ("user", "assistant"):
                s["first_ts"] = s["first_ts"] or ts
                s["last_ts"] = ts
            if m.get("cwd"):
                s["cwd"] = m["cwd"]
            if typ == "user" and not m.get("isMeta") and not m.get("isCompactSummary"):
                p = clean_prompt(text_of(m))
                if p and not (s["prompts"] and s["prompts"][-1][1] == p):  # skip a resubmitted duplicate
                    s["prompts"].append((ts, p))
            elif typ == "assistant":
                t = text_of(m).strip()
                if t:
                    s["last_reply"] = t
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count", type=int, default=4, help="sessions to show in the table (default 4)")
    ap.add_argument("--more", type=int, default=2, help="older sessions to list briefly (default 2)")
    ap.add_argument("--project", default=os.getcwd(), help="project folder (default: current directory)")
    ap.add_argument("--include-current", action="store_true", help="also list the session running this script")
    ap.add_argument("--json", action="store_true", help="print the facts as JSON (input for render.py)")
    a = ap.parse_args(argv)

    project = find_project(a.project)
    if not project:
        print(f"NO_TRANSCRIPTS: no Claude sessions found for {os.path.abspath(a.project)} "
              f"or any folder above it", file=sys.stderr)
        return 1

    current = os.environ.get("CLAUDE_CODE_SESSION_ID")
    want = a.count + a.more

    # File modification time is a cheap first cut, but Claude also writes to a transcript
    # when a session closes, so read a generous shortlist and order by last message.
    by_mtime = sorted(glob.glob(os.path.join(encode(project), "*.jsonl")), key=os.path.getmtime, reverse=True)
    sessions = []
    for f in by_mtime[: max(want * 3, 15)]:
        sid = os.path.basename(f)[:-6]
        if sid == current and not a.include_current:
            continue
        s = read_session(f)
        if s["prompts"]:  # empty or aborted sessions have nothing to resume
            s["id"] = sid
            sessions.append(s)
    sessions.sort(key=lambda s: s["last_ts"] or "", reverse=True)

    live_ids, unnamed = open_sessions()
    now = datetime.datetime.now().astimezone()
    today = now.date()

    if a.json:
        out = {"project": project, "generated": fmt(now, None), "generated_iso": now.isoformat(),
               "current_session": current, "unnamed_claude_processes": unnamed, "sessions": []}
        for n, s in enumerate(sessions[:want], 1):
            last = parse_ts(s["last_ts"])
            idle = (now - last).total_seconds() / 60 if last else None
            out["sessions"].append({
                "rank": n, "tier": "table" if n <= a.count else "more", "id": s["id"], "title": s["title"],
                "started": fmt(parse_ts(s["first_ts"]), today), "last_active": fmt(last, today),
                "idle_minutes": None if idle is None else round(idle),
                "open_now": s["id"] in live_ids,
                "recent": s["id"] not in live_ids and idle is not None and idle < RECENT_MINUTES,
                "last_working_dir": s["cwd"] if s["cwd"] and os.path.abspath(s["cwd"]) != project else None,
                "prompt_count": len(s["prompts"]),
                "first_prompt": one_line(s["prompts"][0][1], 240),
                "recent_prompts": [one_line(p, 240) for _, p in s["prompts"][-3:]],
                "last_reply": one_line(s["last_reply"], 400),
                "resume": f"claude --resume {s['id']}",
            })
        json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0

    print(f"PROJECT {project}" + ("" if project == os.path.abspath(a.project) else f"  (found above {a.project})"))
    print(f"NOW {fmt(now, None)} {now.strftime('%Z')}")
    if current:
        print(f"CURRENT_SESSION {current} ({'included' if a.include_current else 'excluded'})")
    if unnamed is None:
        print("OPEN_CHECK unavailable (no ps) — open status unknown")
    elif unnamed:
        print(f"UNNAMED_CLAUDE_PROCESSES {unnamed} (started without a session ID; one may be this session, "
              f"the others cannot be matched to a row)")

    if not sessions:
        print("NO_RESUMABLE_SESSIONS (transcripts exist but none has a typed prompt)")
    for n, s in enumerate(sessions[:want], 1):
        last = parse_ts(s["last_ts"])
        idle = (now - last).total_seconds() / 60 if last else None
        tier = "TABLE" if n <= a.count else "MORE"
        print("=" * 80)
        print(f"{tier} #{n}  id={s['id']}")
        print(f"title: {s['title'] or '-'}")
        print(f"started: {fmt(parse_ts(s['first_ts']), today)} | last active: {fmt(last, today)}"
              f" | prompts: {len(s['prompts'])} | idle: {'?' if idle is None else f'{idle:.0f} min'}")
        if s["id"] in live_ids:
            print("⚠ OPEN NOW (a claude process is running this session)")
        elif idle is not None and idle < RECENT_MINUTES:
            print("⚠ RECENT (last message under 10 min ago; may still be open)")
        if s["cwd"] and os.path.abspath(s["cwd"]) != project:
            print(f"last working dir: {s['cwd']} (resume from the project folder, not this one)")
        print(f"first prompt: {one_line(s['prompts'][0][1], 240)}")
        if tier == "TABLE":
            for ts, p in s["prompts"][-3:]:
                print(f"recent prompt [{fmt(parse_ts(ts), today)}]: {one_line(p, 240)}")
            print(f"last reply: {one_line(s['last_reply'], 400)}")
        print(f"resume: claude --resume {s['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
