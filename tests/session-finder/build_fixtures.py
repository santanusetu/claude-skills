#!/usr/bin/env python3
"""Build a fake Claude Code config folder with made-up sessions for one project.

Everything here is fictional: a web shop at /home/dev/acme-shop and 7 sessions.
Run it to regenerate fixtures/; the tests and the evals both use that folder via
CLAUDE_CONFIG_DIR, so nobody needs real transcripts to try the skill.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "fixtures")
PROJECT = "/home/dev/acme-shop"
FOLDER = os.path.join(ROOT, "projects", "-home-dev-acme-shop")


def user(ts, text, **extra):
    return {"type": "user", "timestamp": ts, "cwd": extra.pop("cwd", PROJECT),
            "message": {"role": "user", "content": text}, **extra}


def reply(ts, text, **extra):
    return {"type": "assistant", "timestamp": ts, "cwd": extra.pop("cwd", PROJECT),
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}, **extra}


SESSIONS = {
    # 1. Newest. Drifted from a flaky test into CI caching.
    "a1f3c2d4-1111-4a7b-9c10-000000000001": [
        {"type": "ai-title", "aiTitle": "Flaky checkout test"},
        user("2026-01-15T17:02:00Z", "the checkout test keeps failing randomly in CI, can you figure out why?"),
        reply("2026-01-15T17:20:00Z", "It races the payment mock. I added an explicit wait for the mock to be ready."),
        user("2026-01-15T17:40:00Z", "nice. CI is also slow, can we cache node_modules in the GitHub Actions workflow?"),
        reply("2026-01-15T18:05:00Z", "Added dependency caching to .github/workflows/ci.yml; the run dropped from 9 to 4 minutes."),
        user("2026-01-15T18:10:00Z", "open a PR for both"),
        reply("2026-01-15T18:14:00Z", "PR #42 is open with the test fix and the CI cache. It's waiting for your review."),
    ],
    # 2. Waiting on the user to choose something.
    "b2e4d3c5-2222-4b8c-8d21-000000000002": [
        {"type": "ai-title", "aiTitle": "Dark mode settings"},
        user("2026-01-15T14:00:00Z", "add a dark mode toggle to the settings page"),
        reply("2026-01-15T14:30:00Z", "Toggle added and saved per user."),
        user("2026-01-15T15:10:00Z", "can it follow the system theme by default?", cwd=PROJECT + "/web/src"),
        reply("2026-01-15T15:25:00Z", "Done: it now follows the system theme unless the user overrides it. "
              "One thing left for you: pick the accent colour for dark mode (blue or teal).", cwd=PROJECT + "/web/src"),
    ],
    # 3. The user renamed this one; has a duplicate prompt, a subagent message and a bad line.
    "c3d5e4f6-3333-4c9d-9e32-000000000003": [
        {"type": "ai-title", "aiTitle": "auto title that should lose"},
        {"type": "custom-title", "customTitle": "orders status migration"},
        user("2026-01-15T11:00:00Z", "write a database migration that adds a status column to orders"),
        user("2026-01-15T11:00:30Z", "write a database migration that adds a status column to orders"),
        {"type": "user", "timestamp": "2026-01-15T11:01:00Z", "isMeta": True, "message": {"content": "meta noise"}},
        reply("2026-01-15T11:05:00Z", "SUBAGENT TEXT THAT MUST NOT APPEAR", isSidechain=True),
        "this line is not json",
        reply("2026-01-15T11:40:00Z", "Migration 0042_add_order_status is written and tested on a local copy. "
              "It has not been run against staging yet."),
    ],
    # 4. Stopped with a proposed fix not yet applied.
    "d4c6f5a7-4444-4dae-8f43-000000000004": [
        {"type": "ai-title", "aiTitle": "Worker memory leak"},
        user("2026-01-14T20:00:00Z", "the background worker's memory keeps growing until it crashes, help me debug"),
        reply("2026-01-14T21:10:00Z", "Found it: resized image buffers are cached forever in thumbnails.py. "
              "I've proposed an LRU cache capped at 200 entries but haven't applied it. Say 'apply it' to go ahead."),
    ],
    # 5. Started with a slash command.
    "e5b7a6c8-5555-4ebf-a054-000000000005": [
        user("2026-01-14T09:00:00Z", "<command-name>/teach-me</command-name><command-args>websockets</command-args>"),
        reply("2026-01-14T09:30:00Z", "Here's the chapter on WebSockets, ending with 5 check questions."),
    ],
    # 6. Older, multi-day.
    "f6a8b7d9-6666-4fc0-b165-000000000006": [
        user("2026-01-10T16:00:00Z", "set up Stripe webhooks for refunds"),
        reply("2026-01-12T10:00:00Z", "Refund webhooks are live in test mode; the signing secret is read from the environment."),
    ],
    # 7. Empty: opened and closed without a prompt. Must be skipped.
    "a7a7a7a7-7777-4a11-8111-000000000007": [
        {"type": "mode", "mode": "default"},
    ],
}

# Newest first by file time, so the script's cheap first sort has something real to do.
MTIMES = {sid: 1768500000 - i * 3600 for i, sid in enumerate(SESSIONS)}


def build():
    shutil.rmtree(ROOT, ignore_errors=True)
    os.makedirs(FOLDER)
    for sid, entries in SESSIONS.items():
        path = os.path.join(FOLDER, sid + ".jsonl")
        with open(path, "w") as fh:
            for e in entries:
                fh.write((e if isinstance(e, str) else json.dumps(e)) + "\n")
        os.utime(path, (MTIMES[sid], MTIMES[sid]))
    print(f"wrote {len(SESSIONS)} sessions to {FOLDER}")


if __name__ == "__main__":
    build()
