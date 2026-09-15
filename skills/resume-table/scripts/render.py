#!/usr/bin/env python3
"""Render the session table as a local HTML page and open it in the browser.

Inputs:
  --facts      JSON from `sessions.py --json`
  --summaries  JSON written by Claude: {"<session id>": {"about": "...", "stopped": "..."}}
               In both fields **double asterisks** mark emphasis; everything else is escaped.

Output: $CLAUDE_CONFIG_DIR/resume-table/sessions.html (default ~/.claude/...), one
self-contained file with no network requests. Opens it unless --no-open or
RESUME_TABLE_NO_OPEN=1 is set.
"""
import argparse, base64, html, json, os, re, sys, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")


def default_out():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(base, "resume-table", "sessions.html")


def rich(text, tag):
    """Escape text, then turn **x** into <tag>x</tag>. Nothing else is interpreted."""
    parts = re.split(r"\*\*(.+?)\*\*", html.escape(text or "", quote=False))
    return "".join(f"<{tag}>{p}</{tag}>" if i % 2 else p for i, p in enumerate(parts))


def short_path(path):
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if home != "/" and path.startswith(home + os.sep) else path


def span(started, last):
    """'Thu 15 Jan 9:02 AM' + 'Thu 15 Jan 10:14 AM' -> date once, then the 2 times."""
    a, b = (started or "").rsplit(" ", 2), (last or "").rsplit(" ", 2)
    if len(a) == 3 and len(b) == 3 and a[0] == b[0]:
        return f"{a[0]} · ", f"{a[1]} {a[2]}", f"{b[1]} {b[2]}"
    return "", started or "?", last or "?"


def row_html(s, summary):
    esc = lambda t: html.escape(str(t or ""), quote=True)
    if summary and summary.get("about"):
        about = rich(summary["about"], "b")
    else:
        about = (f'<span class="raw">{esc(s.get("title") or s.get("first_prompt"))}</span>'
                 '<span class="note">not summarised</span>')
    if summary and summary.get("stopped"):
        stopped = rich(summary["stopped"], "strong")
    else:
        reply = s.get("last_reply") or ""
        stopped = f'<span class="raw">{esc(reply[:160] + ("…" if len(reply) > 160 else ""))}</span>'
    running = '<div class="running">running in another terminal</div>' if s.get("open_now") else ""
    if s.get("recent") and not s.get("open_now"):
        running = '<div class="running">active in the last 10 minutes · may still be open</div>'
    warn = s.get("open_now") or s.get("recent")
    warnline = ('<p class="warnline" hidden>Still open elsewhere? Switch to that window first, '
                "or the 2 will overwrite each other.</p>") if warn else ""
    label = "Copy anyway" if warn else "Copy"
    day, t0, t1 = span(s.get("started"), s.get("last_active"))
    return (f'<tr class="row{" is-open" if warn else ""}" data-id="{esc(s["id"])}" data-rank="{esc(s["rank"])}">'
            f'<td class="n">{esc(s["rank"])}</td>'
            f'<td class="about">{about}{running}</td>'
            f'<td class="when">{esc(day)}{esc(t0)} → <span class="last">{esc(t1)}</span></td>'
            f'<td class="stop">{stopped}{warnline}</td>'
            f'<td class="act"><button type="button" aria-label="{esc(label)}: claude --resume for session {esc(s["rank"])}">'
            f'{esc(label)}</button></td></tr>')


def build(facts, summaries, theme="system"):
    sessions = facts.get("sessions", [])
    project = short_path(facts.get("project", ""))
    if sessions:
        rows = "".join(row_html(s, summaries.get(s["id"])) for s in sessions)
        body = ('<div class="scroll"><table><caption>Recent Claude Code sessions, newest first</caption>'
                "<thead><tr><th>#</th><th>What it was about</th><th>Started → last active</th>"
                "<th>Where it stopped</th><th class=\"act\"><span hidden>Copy</span></th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div>")
    else:
        body = ('<p class="empty">No sessions found for this folder yet. Start one with <code>claude</code> '
                "here, then run this again.</p>")
    notes = ["<p>Run the copied command from the project folder above. "
             "<code>claude --resume</code> with no ID lists every session instead.</p>"]
    if any(s.get("open_now") for s in sessions):
        notes.append("<p>Sessions marked running are already open in another terminal. Switch to that window "
                     "rather than resuming, or the 2 will overwrite each other.</p>")
    unnamed = facts.get("unnamed_claude_processes")
    if unnamed:
        notes.append(f"<p>{html.escape(str(unnamed))} other Claude window{'s are' if unnamed != 1 else ' is'} open "
                     "without a session ID on its command line, so it can't be matched to a row.</p>")
    with open(os.path.join(ASSETS, "fonts", "MartianMono-Medium.woff2"), "rb") as fh:
        font = base64.b64encode(fh.read()).decode()
    with open(os.path.join(ASSETS, "page.html")) as fh:
        page = fh.read()
    n = len(sessions)
    values = {
        "THEME_ATTR": f' data-theme="{theme}"' if theme in ("dark", "light") else "",
        "PROJECT_SHORT": html.escape(project),
        "COUNT_LABEL": f"{n} session{'s' if n != 1 else ''}",
        "GENERATED": html.escape(facts.get("generated", "")),
        "FIRST_ID": html.escape(sessions[0]["id"]) if sessions else "",
        "BODY": body,
        "NOTES": "".join(notes),
        "FONT_BASE64": font,
    }
    return re.sub(r"\{\{([A-Z_0-9]+)\}\}", lambda m: values[m.group(1)], page)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--facts", required=True)
    ap.add_argument("--summaries", help="optional; rows without a summary show the raw title and last reply")
    ap.add_argument("--out", default=default_out())
    ap.add_argument("--theme", choices=["system", "dark", "light"], default="system")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args(argv)

    with open(a.facts) as fh:
        facts = json.load(fh)
    summaries = {}
    if a.summaries and os.path.exists(a.summaries):
        with open(a.summaries) as fh:
            summaries = json.load(fh)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(build(facts, summaries, a.theme))
    print(f"PAGE {os.path.abspath(a.out)}")
    if not a.no_open and os.environ.get("RESUME_TABLE_NO_OPEN") != "1":
        opened = webbrowser.open("file://" + os.path.abspath(a.out))
        print("OPENED" if opened else "NOT_OPENED (no browser available; give the user the path)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
