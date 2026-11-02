#!/usr/bin/env python3
"""Turn a CricBay scorecard into plain facts for a Player of the Match report.

Prints JSON: match details, both innings, and the things that are easy to get
wrong by hand (partnerships, wicket clusters, hat-tricks, the chase equation at
each wicket). Claude writes the report; this script never judges anything.

    scorecard.py 12345                     render that 1 page with headless Chrome
    scorecard.py --html saved.html         parse a page you saved yourself

It loads the 1 scorecard you name and no other CricBay page.
"""
import argparse, html as htmllib, json, os, re, shutil, subprocess, sys, tempfile

BASE = "https://www.cricbay.com/scorecard/"
BALLS_PER_INNINGS_T20 = 120
CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]


# ---------------------------------------------------------------- fetching

def scorecard_id(value):
    """Accept an id or a cricbay.com scorecard URL. Refuse anything else."""
    m = re.fullmatch(r"(?:https?://(?:www\.)?cricbay\.com/scorecard/)?(\d+)/?", value.strip())
    if not m:
        raise ValueError(value)
    return int(m.group(1))


def find_chrome():
    env = os.environ.get("CHROME_PATH")
    if env:
        return env
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    for name in CHROME_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def render(chrome, match_id):
    """The site is a JavaScript app, so a plain HTTP fetch returns an empty shell."""
    with tempfile.TemporaryDirectory() as profile:
        r = subprocess.run(
            [chrome, "--headless", "--disable-gpu", f"--user-data-dir={profile}",
             "--virtual-time-budget=15000", "--dump-dom", f"{BASE}{match_id}"],
            capture_output=True, text=True, errors="replace", timeout=90,
        )
    return r.stdout


# ---------------------------------------------------------------- parsing

def clean(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", htmllib.unescape(text)).strip()


def strip_noise(page):
    return re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", "", page)


def field(page, label):
    m = re.search(rf">{re.escape(label)}</label><div[^>]*>(.*?)</div></div>", page, re.S)
    return m.group(1) if m else ""


def rows(table):
    return re.findall(r"<tr\b([^>]*)>(.*?)</tr>", table, re.S)


def cells(row):
    return [clean(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)]


def to_int(value):
    m = re.search(r"\d+", value or "")
    return int(m.group()) if m else 0


def parse_pom(page):
    m = re.search(r"PoM</span><div[^>]*>(.*?)</div></div></div></div>", page, re.S)
    if not m:
        return {"name": None, "report": None, "report_by": None}
    block = m.group(1)
    name = clean(re.split(r"<button|<div", block, maxsplit=1)[0]) or None
    report, by = None, None
    body = re.search(r'collapse"><div>(.*?)</div>--\s*<span[^>]*>\s*<b>Umpire:\s*</b>(.*?)</span>', block, re.S)
    if body:
        # Keep the paragraph breaks: clean() would flatten them, and they show the report's shape.
        parts = re.split(r"</p>|<br\s*/?>", body.group(1))
        report = "\n".join(p for p in (clean(part) for part in parts) if p) or None
        by = clean(body.group(2)) or None
    return {"name": name, "report": report, "report_by": by}


def parse_details(page):
    title = re.search(r"<h3>(.*?)(?:<sup>(.*?)</sup>)?</h3>", page, re.S)
    when = field(page, "Date, @Venue")
    umpires = re.findall(
        r'font-weight-bold">\s*([^<]+?)\s*</span><span class="text-secondary mr-1">\(([^<]*)\)</span>',
        field(page, "Umpire(s)"),
    )
    venue = re.search(r'text-success">([^<]+)<', when)
    return {
        "match": clean(title.group(1)) if title else None,
        "stage": clean(title.group(2) or "") or None if title else None,
        "tournament": clean(field(page, "Tournament")),
        "date": clean(when.split("@")[0]) if when else None,
        "venue": clean(venue.group(1)) if venue else None,
        "umpires": [{"name": n, "team": t} for n, t in umpires],
        "toss": clean(field(page, "Toss")),
        "result": clean(field(page, "Result")),
    }


def split_role(name):
    """The batting table says 'Name (c)(w)'; the fall of wickets says 'Name'."""
    roles = re.findall(r"\((c|w)\)", name)
    return re.sub(r"\s*\((?:c|w)\)", "", name).strip(), roles


def parse_batting(section):
    table = re.search(r"<table.*?</table>", section, re.S)
    batters, extras, total = [], None, None
    for attrs, row in rows(table.group(0)) if table else []:
        if "d-sm-none" in attrs:  # the mobile copy of the dismissal line
            continue
        c = cells(row)
        if c and c[0].startswith("Extras"):
            extras = {"detail": c[0], "runs": to_int(c[1])}
        elif c and c[0].startswith("TOTAL"):
            m = re.fullmatch(r"(\d+)(?:/(\d+))?", c[1])
            overs = re.search(r"([\d.]+)\s*Overs", c[0])
            rate = re.search(r"RR:\s*([\d.]+)", c[0])
            total = {"runs": int(m.group(1)) if m else 0,
                     "wickets": int(m.group(2)) if m and m.group(2) else 10,
                     "overs": float(overs.group(1)) if overs else None,
                     "run_rate": float(rate.group(1)) if rate else None}
        elif len(c) == 7:
            name, roles = split_role(c[0])
            batters.append({"name": name, "roles": roles, "dismissal": c[1], "runs": to_int(c[2]), "balls": to_int(c[3]),
                            "fours": to_int(c[4]), "sixes": to_int(c[5]), "strike_rate": c[6]})
    return batters, extras, total


def table_after(section, heading):
    i = section.find(heading)
    m = re.search(r"<table.*?</table>", section[i:], re.S) if i >= 0 else None
    return m.group(0) if m else ""


def parse_bowling(section):
    out = []
    for _, row in rows(table_after(section, "Bowling Figures")):
        c = cells(row)
        if len(c) == 9:
            out.append({"name": c[0], "overs": c[1], "maidens": to_int(c[2]), "runs": to_int(c[3]),
                        "wickets": to_int(c[4]), "hat_trick": "[H]" in c[4], "dots": to_int(c[5]),
                        "wides": to_int(c[6]), "no_balls": to_int(c[7]), "economy": c[8]})
    return out


def parse_powerplay(section):
    out = []
    for _, row in rows(table_after(section, "PowerPlay Overs")):
        c = cells(row)
        if len(c) == 5:
            out.append({"over": to_int(c[0]), "runs": to_int(c[1]), "wickets": to_int(c[2]),
                        "bowler": c[3], "type": c[4]})
    return out


def bowler_of(dismissal):
    m = re.search(r"(?:^|\s|c&)b (.+)$", dismissal or "")  # "b X", "c Y b X", "c&b X"
    return m.group(1).strip() if m else None


def parse_fow(section, batters):
    how = {b["name"]: b["dismissal"] for b in batters}
    out = []
    for wicket, score, name, over in re.findall(
        r"(\d+)-(\d+)\(<span[^>]*>([^<]+)</span>,\s*([\d.]+) ov\)", section
    ):
        name = htmllib.unescape(name).strip()
        over_whole, ball = over.split(".") if "." in over else (over, "0")
        out.append({"wicket": int(wicket), "score": int(score), "batter": name, "over": over,
                    "balls_bowled": int(over_whole) * 6 + int(ball),
                    "in_over_number": int(over_whole) + 1,
                    "dismissal": how.get(name), "bowler": bowler_of(how.get(name))})
    return out


# ---------------------------------------------------------------- derived facts

def partnerships(batters, fow, total):
    """Walk the batting order: when a batter falls, the next one in comes in."""
    if len(batters) < 2:
        return []
    order = [b["name"] for b in batters]
    crease, next_in, start, out = order[:2], 2, 0, []
    for w in fow:
        out.append({"wicket": w["wicket"], "runs": w["score"] - start, "from": start, "to": w["score"],
                    "batters": list(crease), "ended_by": w["batter"]})
        start = w["score"]
        if w["batter"] in crease:
            if next_in < len(order):
                crease[crease.index(w["batter"])] = order[next_in]
                next_in += 1
            else:  # never name a dismissed batter in the next stand
                crease.remove(w["batter"])
    if total and total["wickets"] < 10 and total["runs"] > start:
        out.append({"wicket": len(fow) + 1, "runs": total["runs"] - start, "from": start,
                    "to": total["runs"], "batters": list(crease), "ended_by": None})
    return out


def wicket_clusters(fow):
    """2 or more wickets in a row with no run added between them."""
    out, group = [], []
    for w in fow + [None]:
        if w and group and w["score"] == group[-1]["score"]:
            group.append(w)
            continue
        if len(group) >= 2:
            out.append({"score": group[0]["score"], "wickets": [g["wicket"] for g in group],
                        "overs": [g["over"] for g in group], "batters": [g["batter"] for g in group],
                        "bowlers": [g["bowler"] for g in group]})
        group = [w] if w else []
    return out


def hat_tricks(fow):
    """3 wickets to the same bowler on consecutive balls of one over."""
    out = []
    for a, b, c in zip(fow, fow[1:], fow[2:]):
        same = a["bowler"] and a["bowler"] == b["bowler"] == c["bowler"]
        if same and c["balls_bowled"] - a["balls_bowled"] == 2 and a["in_over_number"] == c["in_over_number"]:
            out.append({"bowler": a["bowler"], "overs": [a["over"], b["over"], c["over"]],
                        "batters": [a["batter"], b["batter"], c["batter"]]})
    return out


def wickets_by_over(fow):
    grouped = {}
    for w in fow:
        if w["bowler"]:
            grouped.setdefault((w["bowler"], w["in_over_number"]), []).append(w["batter"])
    return [{"bowler": k[0], "over_number": k[1], "batters": v} for k, v in sorted(grouped.items(), key=lambda x: x[0][1])]


def parse_innings(page):
    parts = re.split(r'<h4[^>]*>([^<]*?)\s*Innings</h4>', page)
    innings = []
    for team, section in zip(parts[1::2], parts[2::2]):
        batters, extras, total = parse_batting(section)
        fow = parse_fow(section, batters)
        dnb = re.search(r"Did Not Bat :\s*</span><span>(.*?)</span>", section, re.S)
        innings.append({
            "team": clean(team), "total": total, "extras": extras, "batting": batters,
            "did_not_bat": clean(dnb.group(1)) if dnb else None,
            "fall_of_wickets": fow, "bowling": parse_bowling(section), "powerplay_overs": parse_powerplay(section),
            "partnerships": partnerships(batters, fow, total), "wicket_clusters": wicket_clusters(fow),
            "hat_tricks": hat_tricks(fow), "wickets_by_over": wickets_by_over(fow),
        })
    # The chase equation at each wicket. Balls left assumes the full 20 overs.
    if len(innings) == 2 and innings[0]["total"]:
        target = innings[0]["total"]["runs"] + 1
        innings[1]["target"] = target
        for w in innings[1]["fall_of_wickets"]:
            w["runs_needed"] = target - w["score"]
            w["balls_left"] = BALLS_PER_INNINGS_T20 - w["balls_bowled"]
    return innings


def parse(page):
    page = strip_noise(page)
    details = parse_details(page)
    return {**details, "pom": parse_pom(page), "innings": parse_innings(page)}


# ---------------------------------------------------------------- commands

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("match", nargs="?", help="scorecard id or cricbay.com scorecard URL")
    ap.add_argument("--html", help="parse a saved copy of the rendered page instead of fetching")
    args = ap.parse_args(argv)

    if not args.match and not args.html:
        ap.error("give a scorecard id or --html FILE")

    match_id, chrome = None, None
    if args.match:
        try:
            match_id = scorecard_id(args.match)
        except ValueError:
            print(f"BAD_SCORECARD: {args.match!r} is not a CricBay scorecard id or URL", file=sys.stderr)
            return 2

    if args.html:
        with open(args.html, errors="replace") as f:
            page = f.read()
    else:
        chrome = find_chrome()
        if not chrome:
            print("NO_CHROME: install Chrome, set CHROME_PATH, or use --html", file=sys.stderr)
            return 3
        page = render(chrome, match_id)

    facts = parse(page)
    if not facts["match"]:
        print("NO_SCORECARD: the page held no match details. It may not have loaded.", file=sys.stderr)
        return 4
    if not facts["innings"]:
        print(f"NOT_PLAYED: {facts['match']}: {facts['result'] or 'no innings on the card'}", file=sys.stderr)
        return 5

    facts["id"] = match_id
    print(json.dumps(facts, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
