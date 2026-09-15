#!/usr/bin/env python3
"""Build the README example from the fictional fixtures: sessions.html plus 2 screenshots.

Run from the repo root:  python3 examples/resume-table/build_example.py
Screenshots need Google Chrome or Chromium; the HTML does not.
"""
import contextlib, importlib.util, io, json, os, shutil, subprocess, sys
from unittest import mock

import time
os.environ["TZ"] = "America/Los_Angeles"  # fixtures and expected times are written in Pacific time
if hasattr(time, "tzset"):
    time.tzset()
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "examples", "resume-table")
EVALS = os.path.join(ROOT, "evals", "resume-table")
SCRIPTS = os.path.join(ROOT, "skills", "resume-table", "scripts")
sys.path.insert(0, EVALS)
import build_fixtures  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def chrome():
    for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium", "chromium-browser"):
        if os.path.exists(c) or shutil.which(c):
            return c


def main():
    build_fixtures.build()
    sessions, render = load("sessions"), load("render")
    ids = list(build_fixtures.SESSIONS)
    buf = io.StringIO()
    with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": build_fixtures.ROOT}), \
         mock.patch.object(sessions, "open_sessions", return_value=({ids[1]}, 0)), contextlib.redirect_stdout(buf):
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        sessions.main(["--project", "/home/dev/acme-shop", "--count", "10", "--more", "0", "--json"])
    facts = json.loads(buf.getvalue())
    facts["generated"] = "Thu 15 Jan 10:20 AM"  # stable for the screenshots
    with open(os.path.join(EVALS, "example-summaries.json")) as fh:
        summaries = json.load(fh)
    with open(os.path.join(OUT, "sessions.html"), "w") as fh:
        fh.write(render.build(facts, summaries))
    exe = chrome()
    for theme in ("dark", "light"):
        page = os.path.join(OUT, f".tmp-{theme}.html")
        with open(page, "w") as fh:
            fh.write(render.build(facts, summaries, theme))
        if exe:
            subprocess.run([exe, "--headless", "--disable-gpu", "--hide-scrollbars", "--window-size=1320,760",
                            "--virtual-time-budget=1500", f"--screenshot={os.path.join(OUT, f'screenshot-{theme}.png')}",
                            "file://" + page], capture_output=True)
        os.remove(page)
    print("wrote", OUT, "(screenshots skipped: no Chrome)" if not exe else "")


if __name__ == "__main__":
    main()
