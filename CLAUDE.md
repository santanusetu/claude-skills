# claude-skills — conventions

A public collection of Claude Code skills, installable as plugins. Everything here is public, so read the privacy rule first.

## Layout

```
skills/<name>/            the skill itself: SKILL.md + scripts/ (what users install)
evals/<name>/             tests, fictional fixtures, evals.json, README
examples/<name>/          sample output built from the fixtures (README screenshots)
templates/new-skill/      copy this to start a skill
tools/privacy_check.py    blocks commits that contain private terms
.claude-plugin/marketplace.json   one plugin entry per skill
```

**One skill per folder. A skill's folder holds only what gets installed**, since tests and fixtures in `skills/` would be copied onto every user's machine.

## Privacy rule

- **Examples, fixtures, evals and screenshots are fictional.** Never paste real transcripts, names, employers, emails, file paths or session IDs, even to "just test something".
- **Before every commit, run `python3 tools/privacy_check.py`.** It reads your own terms from `.private-patterns`, which is gitignored and never committed, plus built-in checks for home-folder paths and emails. See `.private-patterns.example`.
- **`*-workspace/` folders from skill-creator are gitignored**, because they contain real run outputs. Keep them outside the repo anyway.

## Adding a skill

1. `cp -R templates/new-skill/skill skills/<name>` and `cp -R templates/new-skill/evals evals/<name>`, then fill both in.
2. Write the `description` so it says **what the skill does and when to use it**. That text is what makes Claude pick the skill.
3. Put deterministic work in `scripts/`, with Python stdlib only if possible, and let Claude do the judgement.
4. Add fictional fixtures and `unittest` tests in `evals/<name>/`.
5. Add a plugin entry to `.claude-plugin/marketplace.json` and a row to the table at the top of `README.md`, plus a section below it.
6. Run the checks:
   ```bash
   python3 -m unittest discover -s evals/<name>
   python3 tools/privacy_check.py
   claude plugin validate .
   ```
7. Commit as the repo owner.

## Style

- **Keep SKILL.md under ~200 lines.** Explain *why* rather than stacking MUSTs.
- **The README sample output for a skill must come from its fixtures**, so readers can reproduce it.
