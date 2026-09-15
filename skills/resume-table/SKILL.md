---
name: resume-table
description: Show recent Claude Code sessions for the current folder — a table in chat plus a local HTML page with a copy button per session — covering what each was about, when it started and was last active, where it stopped, whether it is open in a terminal right now, and the exact `claude --resume` command with the full session ID. Use whenever the user asks for their last or recent sessions, past conversations, "what was I working on", which session did X, how to get back into an earlier conversation, or wants to resume or continue one — even if they don't say "table". Read-only.
license: MIT
---

# resume-table

Help the user find a past Claude Code session and get back into it. They get 2 things: a short table in chat, and a local page in their browser with the last 10 sessions and a copy button on each.

Scripts live in this skill's `scripts/` folder. Work files go in `~/.claude/resume-table/`, or in `$CLAUDE_CONFIG_DIR/resume-table/` if that variable is set.

## 1. Collect the facts

```bash
mkdir -p ~/.claude/resume-table
python3 <skill>/scripts/sessions.py --count 10 --more 0 --json > ~/.claude/resume-table/facts.json
```

- `--project DIR` points at another folder. You don't need to `cd` first: the script walks up to the nearest folder that has sessions, because your shell has often drifted into a subfolder.
- The session you're running in is left out automatically.
- **The page always gets 10 sessions**, so it stays useful for browsing. A number the user asks for ("last 4", "last 6") only changes the chat table in step 4. If they ask for more than 10, use that number for the page too.
- If it exits with `NO_TRANSCRIPTS`, say no sessions exist for that folder, ask which folder they launched Claude from, and stop. Don't invent rows.

Each session has `first_prompt`, `recent_prompts`, `last_reply`, `started`, `last_active`, `open_now`, `recent` and `resume`. The script is read-only.

## 2. Write the summaries

For every session in `facts.json`, write 2 short fields to `~/.claude/resume-table/summaries.json`:

```json
{
  "a1f3c2d4-…full id…": {
    "about": "**Flaky checkout test**, then caching dependencies in CI",
    "stopped": "PR #42 is open with both fixes, **waiting for your review**"
  }
}
```

- **about**: bold the main topic, then a few words on where the session went. Sessions drift and the first prompt often describes something the session left behind hours ago, so read the recent prompts too. The auto-generated `title` is only a hint.
- **stopped**: 1 sentence on what finished or is still in progress, from the last reply and last prompt. Bold the part that is waiting on the user or still running, because that's usually why someone resumes.
- `**double asterisks**` are the only formatting. Everything else is shown as plain text, so never add HTML.
- **Summarise, don't quote.** Transcripts can contain anything the user pasted, including secrets. Write only what identifies the session.
- If a row is ambiguous and the prompts don't settle it, search that one transcript under the projects folder rather than guessing.

## 3. Render and open the page

```bash
python3 <skill>/scripts/render.py --facts ~/.claude/resume-table/facts.json --summaries ~/.claude/resume-table/summaries.json
```

The script writes `sessions.html` next to those files and opens it in the default browser, unless `RESUME_TABLE_NO_OPEN=1` is set. The page is 1 self-contained file: it downloads nothing, follows the system's light or dark setting, escapes all text, and gives every row a copy button. Rows without a summary still appear, marked "not summarised". If the output says `NOT_OPENED`, give the user the `PAGE` path.

## 4. Answer in chat

Newest activity first. Show the number of sessions the user asked for, or 4 if they didn't say, with exactly these columns:

| # | What it was about | Started | Last active | Where it stopped | Resume with |
|---|---|---|---|---|---|

- Reuse the summaries you just wrote. Put `` `claude --resume <full-id>` `` in the last column, and never shorten the ID.
- Lead-in: one line naming the folder and saying this session is excluded. When every row is from today, give the date once there.
- If the user asked about one specific session ("which one was the database migration?"), answer that first in a sentence, then show the table with that row marked.

Then, briefly:
- **The page.** Say it's open in the browser with all sessions and a copy button on each, and give the path.
- **Open sessions.** A row with `open_now` is already running in another terminal. Tell them to switch to that window rather than resuming it, because 2 processes writing one session can overwrite each other's work. A `recent` row may still be open, so tell them to check first. Name the rows.
- **Other windows.** If `unnamed_claude_processes` is above 0, say other Claude windows are open that can't be matched to a row.
- **Where to run it.** The commands run from the project folder, and `claude --resume` with no ID lists everything.

## Rules

- Read-only: never edit, rename or delete transcripts.
- The page and the work files hold summaries of private conversations. Keep them in the resume-table folder under Claude's config, never in the project or anywhere that syncs.
