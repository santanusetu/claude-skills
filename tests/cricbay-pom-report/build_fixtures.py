#!/usr/bin/env python3
"""Write the fictional scorecard pages the tests read. Teams and players are invented.

The markup copies the shape of a rendered CricBay scorecard.
Run from anywhere:  python3 tests/cricbay-pom-report/build_fixtures.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures")


def row(label, body):
    return f'<div class="row m-1"><label class="col-form-label">{label}</label><div class="col-md-9 p-1">{body}</div></div>'


def batting(batters, extras, total):
    out = '<table id="T1" class="table"><thead><tr><th>Batter</th></tr></thead><tbody>'
    for name, how, r, b, fours, sixes in batters:
        sr = f"{100 * r / b:.2f}" if b else "0.00"
        out += (f'<tr><td class="text-nowrap">{name}</td><td class="d-none"><span>{how}</span></td>'
                f'<td>{r}</td><td>{b}</td><td>{fours}</td><td>{sixes}</td><td>{sr}</td></tr>'
                f'<tr class="d-sm-none text-secondary"><td colspan="7"><span>{how}</span></td></tr>')
    out += f'<tr><td colspan="2"> <div> <div>{extras[0]} </div></div> </td><td>{extras[1]}</td><td colspan="4">&nbsp;</td></tr>'
    out += f'<tr class="bg-lightgray"><td colspan="2">{total[0]}</td><td>{total[1]}</td><td colspan="4">&nbsp;</td></tr>'
    return out + "</tbody></table>"


def fow(items):
    spans = [f'<span>{w}-{s}(<span class="text-secondary">{n}</span>, {o} ov), </span>' for w, s, n, o in items]
    return '<h5 class="text-secondary">Fall of Wickets</h5>' + "".join(spans)


def bowling(items):
    out = '<h5 class="border-0 text-secondary">Bowling Figures</h5><table id="T2"><thead><tr><th>Bowler</th></tr></thead><tbody>'
    for it in items:
        name, overs, maidens, runs, wkts, dots, wd, nb, eco = it
        out += (f'<tr><td>{name}</td><td>{overs}</td><td>{maidens}</td><td>{runs}</td><td>{wkts}</td>'
                f'<td>{dots}</td><td>{wd}</td><td>{nb}</td><td>{eco}</td></tr>')
    return out + "</tbody></table>"


def powerplay(items):
    out = '<h5 class="border-0 text-secondary">PowerPlay Overs</h5><table id="T3"><thead><tr><th>O#</th></tr></thead><tbody>'
    for over, runs, wkts, name, kind in items:
        out += f'<tr class=""><td>{over}</td><td> {runs}</td><td> {wkts}</td><td>{name}</td><td> {kind}</td></tr>'
    return out + "</tbody></table>"


def details(result, pom_block):
    umpires = ('<span class="text-secondary font-weight-bold"> Nora Wells</span><span class="text-secondary mr-1">(Lake Otters)</span>'
               '<span class="text-secondary font-weight-bold"> Omar Ruiz</span><span class="text-secondary mr-1">(Oak Foxes)</span>')
    return ('<script>window.x = "<h3>not this</h3>"</script>'
            '<h3>Harbor Hawks Vs Mill Creek<sup><span class="badge">Quarter Final</span></sup></h3>'
            + row("Tournament", '2026 Example Open <b>Silver</b><span class="badge">T20</span>')
            + row("Date, @Venue", 'Saturday 03/14/2026<span class="text-danger ml-1">08:30AM</span> @<span class="text-success">Riverside</span>')
            + row("Umpire(s)", umpires)
            + row("Toss", "Won by <b>Mill Creek</b> and elected to <b>Field first</b>")
            + row("Result", result)
            + pom_block)


def pom(name, report=None, by=None):
    button = '<button type="button" class="ml-2 btn">PoM Report</button>' if report else ""
    body = f"<div>{report}</div>" if report else "<div></div>"
    signed = f"{by} at 03/14/2026 08:39:54 PM" if by else ""
    return (f'<div class="row m-1"><span class="col-form-label"><svg><title>x</title></svg> PoM</span>'
            f'<div class="col-md-9 p-1">{name}{button}<div class="bg-lightgreen p-1 collapse">{body}-- '
            f'<span class="text-muted"> <b>Umpire: </b>{signed}</span></div></div></div></div>')


HAWKS = (
    '<h4 class="border-0">Harbor Hawks  Innings</h4>'
    + batting(
        [("Asha Rao (c)", "b Ben Cole", 10, 20, 1, 0), ("Dev Iyer", "c&b Finn Moss", 5, 10, 0, 0),
         ("Gita Nair (w)", "st Hal Ortiz b Ben Cole", 28, 60, 2, 0), ("Ivan Lee", "c Jay Kim b Ben Cole", 7, 29, 0, 0),
         ("Kira Shah", "b Ben Cole", 0, 1, 0, 0), ("Liam Das", "not out", 0, 0, 0, 0)],
        ("Extras (10 wides)", 10), ("TOTAL: (20.0 Overs RR:3.00)", "60/5"),
    )
    + '<div><span class="text-muted">Did Not Bat : </span><span> Mira Sen</span></div>'
    + fow([(1, 10, "Dev Iyer", "4.2"), (2, 30, "Asha Rao", "10.1"), (3, 60, "Gita Nair", "19.4"),
           (4, 60, "Ivan Lee", "19.5"), (5, 60, "Kira Shah", "19.6")])
    + bowling([("Ben Cole", 4, 0, 20, "4 [H]", 12, 5, 0, "5.00"), ("Finn Moss", 4, 1, 12, "1", 14, 2, 0, "3.00"),
               ("Cara Vance", 4, 0, 9, "0", 15, 1, 0, "2.25"), ("Noor Aziz", 4, 0, 10, "0", 14, 1, 0, "2.50"),
               ("Tom Reid", 4, 0, 9, "0", 15, 1, 0, "2.25")])
    + powerplay([(9, 3, 0, "Finn Moss", "BOPP")])
)

CREEK = (
    '<h4 class="border-0">Mill Creek  Innings</h4>'
    + batting(
        [("Ben Cole", "c Dev Iyer b Mira Sen", 12, 20, 1, 0), ("Eli Park", "b Asha Rao", 8, 25, 0, 0),
         ("Finn Moss", "c Liam Das b Asha Rao", 0, 2, 0, 0), ("Hal Ortiz (c)(w)", "c Kira Shah b Asha Rao", 15, 45, 1, 0),
         ("Jay Kim", "not out", 6, 28, 0, 0), ("Nia Hart", "not out", 0, 0, 0, 0)],
        ("Extras (10 wides)", 10), ("TOTAL: (20.0 Overs RR:2.55)", "51/4"),
    )
    + '<div><span class="text-muted">Did Not Bat : </span><span> Cara Vance, Noor Aziz, Tom Reid</span></div>'
    + fow([(1, 12, "Ben Cole", "3.3"), (2, 20, "Eli Park", "8.4"), (3, 20, "Finn Moss", "8.6"), (4, 45, "Hal Ortiz", "16.2")])
    + bowling([("Asha Rao", 4, 2, 12, "3", 0, 2, 0, "3.00"), ("Mira Sen", 4, 0, 15, "1", 0, 2, 0, "3.75"),
               ("Dev Iyer", 4, 0, 10, "0", 0, 2, 0, "2.50"), ("Ivan Lee", 4, 0, 8, "0", 0, 2, 0, "2.00"),
               ("Liam Das", 4, 0, 6, "0", 0, 2, 0, "1.50")])
    + powerplay([(17, 0, 1, "Asha Rao", "BAPP"), (18, 4, 0, "Mira Sen", "BAPP")])
)

PAGES = {
    "no-report.html": details("Harbor Hawks won by 9 runs", pom("Asha Rao")) + HAWKS + CREEK,
    "with-report.html": details(
        "Harbor Hawks won by 9 runs",
        pom("Asha Rao", "<p><strong>Asha &amp; the Hawks</strong></p>\n<p>Asha bowled well.<br><br>Well done!</p>", "Nora Wells"),
    ) + HAWKS + CREEK,
    "not-played.html": details("Match yet to be played", "</div>"),
    "empty-shell.html": "<noscript>You need to enable JavaScript to run this app.</noscript><div id='root'></div>",
}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, body in PAGES.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(f"<html><body>{body}</body></html>\n")
    print(f"wrote {len(PAGES)} pages to {OUT}")
