# Tests

1 folder per skill, all run against fictional data, so no real sessions or accounts are needed.

```bash
# every skill
for d in tests/*/; do python3 -m unittest discover -s "$d"; done

# one skill
python3 -m unittest discover -s tests/session-finder
```

GitHub runs the same loop on every push, plus the privacy check. See [`.github/workflows/test.yml`](../.github/workflows/test.yml).

| Skill | What's covered |
|---|---|
| [`session-finder`](session-finder) | Session parsing, ordering, open-session detection (native and npm installs), and the HTML page: escaping, offline-only, themes, empty state |
