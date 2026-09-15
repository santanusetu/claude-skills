#!/usr/bin/env python3
"""Tests for skills/session-finder/scripts/render.py (the local HTML page).

Run from the repo root:  python3 -m unittest discover -s tests/session-finder
"""
import contextlib, importlib.util, io, json, os, re, tempfile, unittest
from unittest import mock

import time
os.environ["TZ"] = "America/Los_Angeles"  # fixtures and expected times are written in Pacific time
if hasattr(time, "tzset"):
    time.tzset()
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "..", "skills", "session-finder", "scripts")


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


render, sessions = load("render"), load("sessions")
import sys; sys.path.insert(0, HERE)
import build_fixtures  # noqa: E402

IDS = list(build_fixtures.SESSIONS)


def facts(count=10):
    build_fixtures.build()
    out = io.StringIO()
    with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": build_fixtures.ROOT}), \
         mock.patch.object(sessions, "open_sessions", return_value=({IDS[1]}, 0)), \
         contextlib.redirect_stdout(out):
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        sessions.main(["--project", "/home/dev/acme-shop", "--count", str(count), "--more", "0", "--json"])
    return json.loads(out.getvalue())


class JsonFactsTest(unittest.TestCase):
    def test_json_shape(self):
        f = facts()
        self.assertEqual([s["id"] for s in f["sessions"]], IDS[:6])
        s = f["sessions"][0]
        for key in ("rank", "started", "last_active", "open_now", "recent", "first_prompt",
                    "recent_prompts", "last_reply", "resume"):
            self.assertIn(key, s)
        self.assertEqual(s["resume"], f"claude --resume {IDS[0]}")
        self.assertTrue(f["sessions"][1]["open_now"])


class RenderTest(unittest.TestCase):
    def setUp(self):
        self.facts = facts()
        self.summaries = {IDS[0]: {"about": "**Flaky test**, then CI", "stopped": "PR open, **waiting for review**"}}

    def page(self, summaries=None, theme="system"):
        return render.build(self.facts, self.summaries if summaries is None else summaries, theme)

    def test_every_session_has_a_row_and_full_copy_id(self):
        html = self.page()
        self.assertEqual(html.count('<tr class="row'), 6)
        for sid in IDS[:6]:
            self.assertIn(f'data-id="{sid}"', html)

    def test_summaries_and_emphasis(self):
        html = self.page()
        self.assertIn("<b>Flaky test</b>, then CI", html)
        self.assertIn("<strong>waiting for review</strong>", html)

    def test_rows_without_summary_fall_back_honestly(self):
        html = self.page()
        self.assertIn("not summarised", html)
        self.assertIn("Dark mode settings", html)  # the session's own title

    def test_text_is_escaped(self):
        evil = {IDS[0]: {"about": "<script>alert(1)</script> **<img src=x onerror=1>**",
                         "stopped": '"><svg onload=1>'}}
        html = self.page(evil)
        body = html.split("<tbody>")[1].split("</tbody>")[0]
        self.assertNotIn("<script>", body)
        self.assertNotIn("<img", body)
        self.assertNotIn("<svg", body)
        self.assertIn("&lt;script&gt;", body)

    def test_open_session_gets_copy_anyway_and_warning(self):
        html = self.page()
        row = re.search(rf'<tr class="row is-open" data-id="{IDS[1]}".*?</tr>', html).group(0)
        self.assertIn("Copy anyway", row)
        self.assertIn("running in another terminal", row)
        self.assertIn('class="warnline" hidden', row)

    def test_fully_offline(self):
        html = self.page()
        self.assertIsNone(re.search(r"(src|href)=[\"']?https?://", html))
        self.assertNotIn("@import", html)
        self.assertIn("data:font/woff2;base64,", html)

    def test_theme_follows_system_unless_forced(self):
        self.assertIn("prefers-color-scheme:dark", self.page())
        self.assertNotIn('data-theme="', self.page().split("<head>")[0])
        self.assertIn('<html lang="en" data-theme="dark">', self.page(theme="dark"))

    def test_no_placeholders_left(self):
        self.assertNotRegex(self.page(), r"\{\{[A-Z_]+\}\}")

    def test_same_day_shown_once(self):
        html = self.page()
        self.assertIn("Thu 15 Jan · 9:02 AM → <span class=\"last\">10:14 AM</span>", html)

    def test_empty_state(self):
        html = render.build({"project": "/home/dev/x", "generated": "now", "sessions": []}, {})
        self.assertIn("No sessions found for this folder yet", html)

    def test_main_writes_under_config_dir_and_respects_no_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = os.path.join(tmp, "facts.json")
            with open(fp, "w") as fh:
                json.dump(self.facts, fh)
            out = io.StringIO()
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": tmp, "SESSION_FINDER_NO_OPEN": "1"}), \
                 mock.patch.object(render.webbrowser, "open") as opener, contextlib.redirect_stdout(out):
                render.main(["--facts", fp, "--out", render.default_out()])
            self.assertTrue(os.path.exists(os.path.join(tmp, "session-finder", "sessions.html")))
            opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
