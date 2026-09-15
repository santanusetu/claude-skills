#!/usr/bin/env python3
"""Tests for skills/session-finder/scripts/sessions.py against the fictional fixtures.

Run from the repo root:  python3 -m unittest discover -s tests/session-finder
"""
import contextlib, importlib.util, io, os, subprocess, sys, unittest
from unittest import mock

import time
os.environ["TZ"] = "America/Los_Angeles"  # fixtures and expected times are written in Pacific time
if hasattr(time, "tzset"):
    time.tzset()
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "..", "skills", "session-finder", "scripts", "sessions.py")
sys.path.insert(0, HERE)
import build_fixtures  # noqa: E402

spec = importlib.util.spec_from_file_location("sessions", SCRIPT)
sessions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sessions)

IDS = list(build_fixtures.SESSIONS)


def run(*args, current=None, ps=""):
    env = {"CLAUDE_CONFIG_DIR": build_fixtures.ROOT}
    if current:
        env["CLAUDE_CODE_SESSION_ID"] = current
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.dict(os.environ, env, clear=False), \
         mock.patch.object(sessions, "open_sessions", return_value=sessions.parse_ps(ps)), \
         contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        if not current:
            os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        code = sessions.main(list(args))
    return code, out.getvalue(), err.getvalue()


def rows(out, tier=None):
    return [l.split("id=")[1] for l in out.splitlines()
            if "id=" in l and (tier is None or l.startswith(tier))]


class SessionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_fixtures.build()

    def test_default_table_and_older_list(self):
        code, out, _ = run("--project", "/home/dev/acme-shop")
        self.assertEqual(code, 0)
        self.assertEqual(rows(out, "TABLE"), IDS[:4])
        self.assertEqual(rows(out, "MORE"), IDS[4:6])

    def test_count_and_more(self):
        _, out, _ = run("--project", "/home/dev/acme-shop", "--count", "2", "--more", "0")
        self.assertEqual(rows(out), IDS[:2])

    def test_orders_by_last_message_not_file_time(self):
        # Touch the oldest session's file so it has the newest mtime; order must not change.
        path = os.path.join(build_fixtures.FOLDER, IDS[5] + ".jsonl")
        os.utime(path, (2000000000, 2000000000))
        try:
            _, out, _ = run("--project", "/home/dev/acme-shop", "--count", "6", "--more", "0")
            self.assertEqual(rows(out), IDS[:6])
        finally:
            build_fixtures.build()

    def test_current_session_excluded_and_includable(self):
        _, out, _ = run("--project", "/home/dev/acme-shop", "--count", "6", "--more", "0", current=IDS[0])
        self.assertNotIn(IDS[0], rows(out))
        self.assertIn(f"CURRENT_SESSION {IDS[0]} (excluded)", out)
        _, out, _ = run("--project", "/home/dev/acme-shop", "--count", "1", "--more", "0",
                        "--include-current", current=IDS[0])
        self.assertEqual(rows(out), [IDS[0]])

    def test_empty_session_skipped(self):
        _, out, _ = run("--project", "/home/dev/acme-shop", "--count", "20", "--more", "0")
        self.assertNotIn(IDS[6], out)
        self.assertEqual(len(rows(out)), 6)

    def test_walks_up_from_subfolder(self):
        code, out, _ = run("--project", "/home/dev/acme-shop/web/src", "--count", "1")
        self.assertEqual(code, 0)
        self.assertIn("PROJECT /home/dev/acme-shop  (found above", out)

    def test_no_transcripts(self):
        code, out, err = run("--project", "/nowhere/at/all")
        self.assertEqual(code, 1)
        self.assertIn("NO_TRANSCRIPTS", err)

    def test_transcript_parsing(self):
        _, out, _ = run("--project", "/home/dev/acme-shop", "--count", "6", "--more", "0")
        self.assertIn("title: orders status migration", out)            # custom title beats ai title
        self.assertNotIn("SUBAGENT TEXT", out)                           # sidechain ignored
        self.assertNotIn("meta noise", out)                              # meta ignored
        self.assertIn("first prompt: /teach-me websockets", out)         # slash command rendered
        block = out.split(IDS[2])[1].split("=" * 80)[0]
        self.assertIn("prompts: 1 ", block)                              # duplicate prompt counted once
        self.assertIn("last working dir: /home/dev/acme-shop/web/src", out)

    def test_open_detection(self):
        ps = (f"/usr/local/bin/claude --resume {IDS[1]}\n"
              "claude\n"
              "/usr/local/bin/claude --chrome-native-host\n"
              "claude -p 'one shot'\n"
              "vim notes.txt\n")
        _, out, _ = run("--project", "/home/dev/acme-shop", "--count", "3", "--more", "0", ps=ps)
        block = out.split(IDS[1])[1].split("=" * 80)[0]
        self.assertIn("OPEN NOW", block)
        self.assertEqual(out.count("OPEN NOW"), 1)
        self.assertIn("UNNAMED_CLAUDE_PROCESSES 1", out)

    def test_open_detection_for_npm_installs(self):
        """npm installs run through node, so ps shows the runtime first."""
        ps = (f"node /opt/homebrew/bin/claude --resume {IDS[0]}\n"
              f"/usr/bin/node /usr/lib/node_modules/@anthropic-ai/claude-code/cli.js -r {IDS[2]}\n"
              f"bun /home/dev/.bun/bin/claude --resume {IDS[3]}\n"
              "node /opt/homebrew/bin/claude\n"
              f"node /home/dev/other-app/cli.js --resume {IDS[4]}\n"   # not Claude Code
              f"node /opt/homebrew/bin/claude -p 'one shot' --resume {IDS[5]}\n")
        ids, unnamed = sessions.parse_ps(ps)
        self.assertEqual(ids, {IDS[0], IDS[2], IDS[3]})
        self.assertEqual(unnamed, 1)

    def test_desktop_app_is_not_a_session(self):
        ps = ("/Applications/Claude.app/Contents/MacOS/Claude\n"
              "/Applications/Claude.app/Contents/Frameworks/Claude Helper.app/Contents/MacOS/Claude Helper --type=gpu-process\n"
              "/Applications/Claude.app/Contents/Frameworks/Claude Helper (Renderer).app/Contents/MacOS/Claude Helper (Renderer) --type=renderer\n"
              "claude\n")
        self.assertEqual(sessions.parse_ps(ps), (set(), 1))

    def test_cli_runs_as_a_script(self):
        r = subprocess.run([sys.executable, SCRIPT, "--project", "/home/dev/acme-shop", "--count", "1"],
                           env={**os.environ, "CLAUDE_CONFIG_DIR": build_fixtures.ROOT},
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"resume: claude --resume {IDS[0]}", r.stdout)


if __name__ == "__main__":
    unittest.main()
