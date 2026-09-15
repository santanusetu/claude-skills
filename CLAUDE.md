# claude-skills — conventions

A public collection of Claude Code skills, installable as plugins. Everything here is public, so read the privacy rule first.

## Layout

```
skills/<name>/                    the skill: SKILL.md + scripts/ + assets/ (what users install)
tests/<name>/                     unit tests, fictional fixtures, evals.json, screenshot builder
template/                         copy this to start a skill (SKILL.md, scripts/, tests/)
.claude-plugin/marketplace.json   one plugin entry per skill
.github/workflows/                CI: every skill's tests + the privacy check
.github/scripts/privacy_check.py  blocks commits that contain private terms
.github/media/                    images used by README.md
```

**One skill per folder. A skill's folder holds only what gets installed**, since tests and fixtures in `skills/` would be copied onto every user's machine. Repo tooling lives under `.github/` so the top level stays clean.

## Privacy rule

- **Examples, fixtures, evals and screenshots are fictional.** Never paste real transcripts, names, employers, emails, file paths or session IDs, even to "just test something".
- **Before every commit, run `python3 .github/scripts/privacy_check.py`.** It reads your own terms from `.private-patterns` at the repo root, which is gitignored and never committed, plus built-in checks for home-folder paths and emails. Start from `.github/private-patterns.example`.
- **`*-workspace/` folders from skill-creator are gitignored**, because they contain real run outputs. Keep them outside the repo anyway.

## Adding a skill

1. Copy the template into place:
   ```bash
   mkdir -p skills/<name> tests/<name>
   cp -R template/SKILL.md template/scripts skills/<name>/
   cp template/tests/* tests/<name>/
   ```
   Then fill both in.
2. Write the `description` so it says **what the skill does and when to use it**. That text is what makes Claude pick the skill.
3. Put deterministic work in `scripts/`, with Python stdlib only if possible, and let Claude do the judgement.
4. Add fictional fixtures and `unittest` tests in `tests/<name>/`.
5. Add a plugin entry to `.claude-plugin/marketplace.json`, and the skill to `README.md`: a line under **Skills** plus its own section below.
6. Run the checks:
   ```bash
   python3 -m unittest discover -s tests/<name>
   python3 .github/scripts/privacy_check.py
   claude plugin validate .
   ```
7. Commit as the repo owner.

## Style

- **Keep SKILL.md under ~200 lines.** Explain *why* rather than stacking MUSTs.
- **The README screenshots for a skill must come from its fixtures**, so readers can reproduce them. Store them in `.github/media/<name>-*.png`.
