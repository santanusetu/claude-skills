#!/usr/bin/env python3
"""Fail if tracked or staged files contain private terms.

Terms come from .private-patterns (one regex per line, # for comments). That file is
gitignored, so the list of things you want kept private is itself never published.
Built-in checks catch home-folder paths and email addresses in any case.

Usage:  python3 tools/privacy_check.py        (exit 1 if anything is found)
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILTIN = [
    (r"/Users/[A-Za-z0-9._-]+", "macOS home path"),
    (r"/home/(?!dev/)[A-Za-z0-9._-]+", "Linux home path (fixtures use /home/dev)"),
    (r"C:\\\\Users\\\\", "Windows home path"),
    (r"[A-Za-z0-9._%+-]+@(?!example\.com|anthropic\.com)[A-Za-z0-9.-]+\.[a-z]{2,}", "email address"),
]
SKIP = {"tools/privacy_check.py", ".private-patterns.example"}


def files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f and f not in SKIP]


def patterns():
    pats = list(BUILTIN)
    path = os.path.join(ROOT, ".private-patterns")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#"):
                pats.append((line, "private term"))
    else:
        print("note: no .private-patterns file; only built-in checks ran "
              "(copy .private-patterns.example to add your own terms)")
    return [(re.compile(p, re.I), why) for p, why in pats]


def main():
    pats, hits = patterns(), 0
    for f in files():
        try:
            text = open(os.path.join(ROOT, f), errors="ignore").read()
        except (IsADirectoryError, FileNotFoundError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for rx, why in pats:
                m = rx.search(line)
                if m:
                    hits += 1
                    print(f"{f}:{n}: {why}: {m.group(0)!r}")
    print(f"{'FAIL' if hits else 'OK'}: {hits} finding(s) in {len(files())} files")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
