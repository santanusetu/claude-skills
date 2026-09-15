#!/usr/bin/env python3
"""Deterministic part of the skill. Print plain facts; let Claude write the judgement."""
import argparse, sys


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args(argv)
    print("replace me")
    return 0


if __name__ == "__main__":
    sys.exit(main())
