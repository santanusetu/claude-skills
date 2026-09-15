#!/usr/bin/env python3
"""Tests for skills/<name>/scripts/main.py. Use fictional fixtures only.

Run from the repo root:  python3 -m unittest discover -s evals/<name>
"""
import os, subprocess, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = os.path.basename(HERE)
SCRIPT = os.path.join(HERE, "..", "..", "skills", NAME, "scripts", "main.py")


class MainTest(unittest.TestCase):
    def test_runs(self):
        r = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
