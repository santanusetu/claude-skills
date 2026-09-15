#!/usr/bin/env python3
"""Rebuild the README screenshots of the session-finder page from the fictional fixtures.

Run from the repo root:  python3 tests/session-finder/build_example.py
Needs Google Chrome or Chromium for the screenshots.
"""
import contextlib, importlib.util, io, json, os, shutil, subprocess, sys
from unittest import mock

import time
os.environ["TZ"] = "America/Los_Angeles"  # fixtures and expected times are written in Pacific time
if hasattr(time, "tzset"):
    time.tzset()
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, ".github", "media")
EVALS = os.path.join(ROOT, "tests", "session-finder")
SCRIPTS = os.path.join(ROOT, "skills", "session-finder", "scripts")
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


def example_facts():
    """Facts and summaries for the fictional sessions, with session 2 marked as open elsewhere."""
    build_fixtures.build()
    sessions = load("sessions")
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
    return facts, summaries


def example_html(theme):
    facts, summaries = example_facts()
    return load("render").build(facts, summaries, theme)


def main():
    exe = chrome()
    for theme in ("dark", "light"):
        page = os.path.join(OUT, f".tmp-{theme}.html")
        with open(page, "w") as fh:
            fh.write(example_html(theme))
        if exe:
            subprocess.run([exe, "--headless", "--disable-gpu", "--hide-scrollbars", "--window-size=1320,760",
                            "--virtual-time-budget=1500", f"--screenshot={os.path.join(OUT, f'session-finder-{theme}.png')}",
                            "file://" + page], capture_output=True)
        os.remove(page)
    print("wrote", OUT, "(screenshots skipped: no Chrome)" if not exe else "")


if __name__ == "__main__":
    main()
