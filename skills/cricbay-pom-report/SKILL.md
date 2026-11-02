---
name: cricbay-pom-report
description: Draft a Player of the Match report for a CricBay game from its scorecard. Reads that one scorecard, works out the moments that decided the game (partnerships, wicket clusters, hat-tricks, the chase equation), and hands back a draft to paste into the site. Use whenever the user umpired a CricBay game and needs a PoM report, pastes a cricbay.com/scorecard link and asks for a write-up, or asks who should be Player of the Match in a CricBay game. It never posts anything.
license: MIT
---

# cricbay-pom-report

CricBay umpires write a Player of the Match report after each game, and the form warns that a one-liner may be deleted. A good report says who the contenders were, walks through both innings, and explains the pick from what actually happened. The numbers that make that convincing, such as who was batting together and what was needed when a wicket fell, are tedious to work out and easy to get wrong, so a script does them.

`<skill>` below means this skill's folder.

## 1. Collect the facts

```bash
python3 <skill>/scripts/scorecard.py <id or URL>
```

The site is a JavaScript app, so the script renders the page with headless Chrome. It loads only this 1 scorecard, because everything the report needs is on it and there is no reason to put more load on a league's site. It prints JSON: match details, the current PoM, any existing report and who filed it (`pom.report_by`), both innings, and these derived facts:

- `partnerships`: runs and the 2 batters, for each wicket
- `wicket_clusters`: wickets falling with no run added
- `hat_tricks` and `wickets_by_over`
- `runs_needed` and `balls_left` at each wicket of the chase
- `powerplay_overs`: a row with `runs` 0 is a maiden, the only over-by-over figure the card gives
- `total.run_rate` and `target`
- `hat_trick` on a bowler: the card's own `[H]` marker

`dots` is sometimes not recorded, usually in the second innings. If a bowler with maidens shows 0, ignore dot balls for that innings.

If it fails, the exit code and a named message on stderr say why:

| Exit | Message | Meaning | What to do |
|---|---|---|---|
| 2 | `BAD_SCORECARD` | Not a CricBay scorecard id or URL | Ask for the scorecard link |
| 3 | `NO_CHROME` | No browser found | If the Claude in Chrome tools are available, save that page's rendered HTML to a file and pass `--html FILE`. Otherwise ask the user to install Chrome |
| 4 | `NO_SCORECARD` | The page did not load | Retry once, then say the page wouldn't load |
| 5 | `NOT_PLAYED` | No innings on the card | Pass on the result text from the message and stop. Don't assume it's still to come, since a game may have been abandoned |

Always name the 2 teams in your reply, so the user can spot a wrong id. With `--html` the script can't confirm which game the file is, so check that the teams match what they asked for.

## 2. Check before writing

- **Is a report already there?** If `pom.report` is filled in, show it word for word with `pom.report_by`, ask whether they still want a new one, and stop until they answer. You can't tell from the card whether a new report replaces the old one, so say that too.
- **Who is the pick?** Use `pom.name` when it is set, since the umpires may already have chosen. If another player's figures look stronger, still write the case for the pick and raise it in step 5, because the decision belongs to the umpires. If `pom.name` is empty, propose the strongest candidate with your reasons and ask them to confirm before writing.
- **Is this user an umpire?** `umpires` lists them. Only mention it if the user has given a name that isn't on the list, since only umpires file reports. Don't ask otherwise.

## 3. Find what decided the game

Read the facts for the 2 or 3 strongest performances, including from the losing side. Look past the raw figures:

- Ask what each wicket changed. One that broke a set partnership or swung a chase usually counts for more than one at the very end of an innings, though a late hat-trick can still cost a side a strong finish.
- Compare a bowler's economy with `total.run_rate` for the innings they bowled in, not with a general idea of a good one. If it isn't better, argue from something else.
- In a close game, say what small contributions were worth against the margin.
- Quote the chase equation from `runs_needed` and `balls_left` rather than working it out yourself.

## 4. Write the draft

Read `<skill>/assets/sample-reports.md` for tone and length, then follow this shape, adjusted to the game:

1. Name the contenders, and the pick if it was close.
2. First innings: the toss, the total, who made it happen.
3. Second innings: the key moments in order.
4. Why this player, including why not the other contenders.

Aim for 100 to 200 words in plain language, with the numbers carrying the argument. Put it in one fenced code block with no markdown inside, so it pastes cleanly into the site's form.

The samples are invented, so never carry a name or a number over from them. Common cricket phrases are fine, but write your own sentences.

## 5. Hand it over

Below the draft, list what the user should check:

- **Anything only an umpire saw:** the pitch, the conditions, standout catches or fielding. Offer to add them.
- **A stronger-looking rival:** if another player's figures beat the pick's, say so, and say the case rests on your reading of the game.
- **Anything you inferred:** say so plainly, for example a reason for the pick that the card doesn't state.
- **Anything on the card that contradicts itself:** for example a team total that doesn't match its batting and extras. Mention it, and leave only that figure out of the draft.
- **The other umpire:** if there are 2, one of them may already be writing a report.

## Rules

- **Read only the scorecard you were given.** Don't open other CricBay pages or earlier games for extra context.
- **Only state what the card shows.** You weren't at the game. A claim like "the pitch was slow" or "he kept his nerve" sounds fine until the umpire who was there reads it, so leave those for them to add.
- **Use names, not "he" or "she".** The card doesn't give anyone's gender, and a wrong guess in a public report is worse than a repeated name. Use a pronoun only if the umpire tells you which one.
- **Don't say who bowled an over unless the data does.** A wicket or a powerplay row shows who bowled that over. The rest cannot be recovered, and only a powerplay row can show a maiden.
- **Stay fair to the losing side.** These reports are public, and the players read them.
- **Never post or submit.** The site needs the umpire's login, and the report goes out under their name, so they paste it themselves.
