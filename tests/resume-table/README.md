# resume-table evals

2 kinds of check, both run against **fictional** sessions, so nothing here depends on your own transcripts.

## 1. Script tests

```bash
python3 -m unittest discover -s tests/resume-table
```

`build_fixtures.py` writes 7 made-up sessions for a project at `/home/dev/acme-shop` into `fixtures/`, and the tests point the script at them with `CLAUDE_CONFIG_DIR`. Rebuild the fixtures with `python3 tests/resume-table/build_fixtures.py`.

## 2. Skill evals (Claude runs the skill)

`evals.json` holds 3 realistic requests with the expected result. The skill's script reads the fixtures when `CLAUDE_CONFIG_DIR` points at them. See what Claude will be summarising with:

```bash
CLAUDE_CONFIG_DIR="$PWD/tests/resume-table/fixtures" \
  python3 skills/resume-table/scripts/sessions.py --project /home/dev/acme-shop
```

For a full with-skill vs without-skill comparison, use Anthropic's [`skill-creator`](https://github.com/anthropics/skills) with these prompts and tell each run to pass `--project /home/dev/acme-shop` with `CLAUDE_CONFIG_DIR` set as above.

**What a good answer does:**
- Uses the 6 columns in order: `# · What it was about · Started · Last active · Where it stopped · Resume with`
- Gives full 36-character session IDs, and every ID is a real fixture session
- Orders rows by last activity and honours the requested count
- Leaves out the empty session (`a7a7a7a7-…`)
- Answers a "which session did X" question first, then shows the table
