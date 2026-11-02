#!/usr/bin/env python3
"""Tests for skills/cricbay-pom-report/scripts/scorecard.py. Fictional fixtures only.

Run from the repo root:  python3 -m unittest discover -s tests/cricbay-pom-report
"""
import json, os, stat, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "..", "skills", "cricbay-pom-report", "scripts")
SCRIPT = os.path.join(SCRIPTS, "scorecard.py")
sys.path.insert(0, SCRIPTS)
import scorecard  # noqa: E402


def load(name):
    with open(os.path.join(HERE, "fixtures", name)) as f:
        return scorecard.parse(f.read())


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


class DetailsTest(unittest.TestCase):
    def setUp(self):
        self.facts = load("no-report.html")

    def test_match_details(self):
        self.assertEqual(self.facts["match"], "Harbor Hawks Vs Mill Creek")
        self.assertEqual(self.facts["stage"], "Quarter Final")
        self.assertEqual(self.facts["venue"], "Riverside")
        self.assertEqual(self.facts["result"], "Harbor Hawks won by 9 runs")
        self.assertIn("Field first", self.facts["toss"])

    def test_both_umpires(self):
        self.assertEqual([u["name"] for u in self.facts["umpires"]], ["Nora Wells", "Omar Ruiz"])
        self.assertEqual(self.facts["umpires"][1]["team"], "Oak Foxes")

    def test_pick_with_no_report(self):
        self.assertEqual(self.facts["pom"], {"name": "Asha Rao", "report": None, "report_by": None})

    def test_existing_report_is_found_and_signed(self):
        pom = load("with-report.html")["pom"]
        self.assertEqual(pom["name"], "Asha Rao")
        self.assertIn("Asha & the Hawks", pom["report"])
        self.assertEqual(pom["report"].split("\n"), ["Asha & the Hawks", "Asha bowled well.", "Well done!"])
        self.assertTrue(pom["report_by"].startswith("Nora Wells"))


class InningsTest(unittest.TestCase):
    def setUp(self):
        self.first, self.second = load("no-report.html")["innings"]

    def test_mobile_duplicate_rows_are_skipped(self):
        self.assertEqual([b["name"] for b in self.first["batting"]][:2], ["Asha Rao", "Dev Iyer"])
        self.assertEqual(len(self.first["batting"]), 6)

    def test_captain_and_keeper_marks_are_split_from_the_name(self):
        self.assertEqual(self.first["batting"][0]["name"], "Asha Rao")
        self.assertEqual(self.first["batting"][0]["roles"], ["c"])
        self.assertEqual(self.second["batting"][3]["name"], "Hal Ortiz")
        self.assertEqual(self.second["batting"][3]["roles"], ["c", "w"])
        # Marked batters must still join up with the plain name in the fall of wickets.
        self.assertEqual(self.second["fall_of_wickets"][3]["bowler"], "Asha Rao")

    def test_totals_and_extras(self):
        self.assertEqual(self.first["total"], {"runs": 60, "wickets": 5, "overs": 20.0, "run_rate": 3.0})
        self.assertEqual(self.first["extras"]["runs"], 10)
        self.assertEqual(self.first["did_not_bat"], "Mira Sen")

    def test_bowling_keeps_the_hat_trick_flag_apart_from_the_count(self):
        ben = self.first["bowling"][0]
        self.assertEqual((ben["wickets"], ben["hat_trick"]), (4, True))
        self.assertFalse(self.first["bowling"][1]["hat_trick"])

    def test_bowler_comes_from_the_dismissal(self):
        self.assertEqual(self.first["fall_of_wickets"][2]["bowler"], "Ben Cole")  # stumped
        self.assertEqual(self.second["fall_of_wickets"][2]["bowler"], "Asha Rao")  # caught

    def test_caught_and_bowled_and_run_out(self):
        self.assertEqual(self.first["fall_of_wickets"][0]["bowler"], "Finn Moss")  # c&b
        self.assertEqual(scorecard.bowler_of("lbw b Finn Moss"), "Finn Moss")
        self.assertIsNone(scorecard.bowler_of("run out Finn Moss"))
        self.assertIsNone(scorecard.bowler_of("not out"))

    def test_powerplay_maiden(self):
        self.assertEqual(self.second["powerplay_overs"][0], {"over": 17, "runs": 0, "wickets": 1, "bowler": "Asha Rao", "type": "BAPP"})


class DerivedTest(unittest.TestCase):
    def setUp(self):
        self.first, self.second = load("no-report.html")["innings"]

    def test_partners_follow_the_batting_order(self):
        p = self.first["partnerships"]
        self.assertEqual(p[0]["batters"], ["Asha Rao", "Dev Iyer"])
        self.assertEqual(p[1]["batters"], ["Asha Rao", "Gita Nair"])
        self.assertEqual((p[2]["batters"], p[2]["runs"]), (["Ivan Lee", "Gita Nair"], 30))

    def test_unbroken_stand_is_included_only_when_it_scored(self):
        self.assertEqual(self.first["partnerships"][-1]["wicket"], 5)  # 60/5, nothing after
        last = self.second["partnerships"][-1]
        self.assertEqual((last["runs"], last["ended_by"]), (6, None))  # 51/4 after 45/4

    def test_a_dismissed_batter_is_never_named_in_the_next_stand(self):
        batters = [{"name": "A"}, {"name": "B"}, {"name": "C"}]  # a card missing a batter
        fow = [{"wicket": 1, "score": 5, "batter": "A"}, {"wicket": 2, "score": 9, "batter": "B"}]
        total = {"runs": 12, "wickets": 2}
        stands = scorecard.partnerships(batters, fow, total)
        self.assertEqual(stands[-1]["batters"], ["C"])
        self.assertEqual(sum(s["runs"] for s in stands), 12)

    def test_clusters(self):
        self.assertEqual(self.first["wicket_clusters"][0]["wickets"], [3, 4, 5])
        self.assertEqual(self.second["wicket_clusters"][0]["wickets"], [2, 3])
        self.assertEqual(self.second["wicket_clusters"][0]["score"], 20)

    def test_hat_trick_needs_the_same_bowler_on_consecutive_balls(self):
        self.assertEqual(self.first["hat_tricks"][0]["bowler"], "Ben Cole")
        self.assertEqual(self.first["hat_tricks"][0]["overs"], ["19.4", "19.5", "19.6"])
        self.assertEqual(self.second["hat_tricks"], [])  # 2 in 8.4 to 8.6 is not 3

    def test_two_wickets_in_one_over(self):
        over_9 = [w for w in self.second["wickets_by_over"] if w["over_number"] == 9]
        self.assertEqual(over_9[0], {"bowler": "Asha Rao", "over_number": 9, "batters": ["Eli Park", "Finn Moss"]})

    def test_chase_equation(self):
        self.assertEqual(self.second["target"], 61)
        w = self.second["fall_of_wickets"][3]  # 45/4 at 16.2
        self.assertEqual((w["runs_needed"], w["balls_left"]), (16, 22))
        self.assertNotIn("runs_needed", self.first["fall_of_wickets"][0])


class CommandLineTest(unittest.TestCase):
    def fixture(self, name):
        return os.path.join(HERE, "fixtures", name)

    def test_prints_json(self):
        r = run("--html", self.fixture("no-report.html"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["pom"]["name"], "Asha Rao")

    def test_not_played(self):
        r = run("--html", self.fixture("not-played.html"))
        self.assertEqual(r.returncode, 5)
        self.assertIn("NOT_PLAYED", r.stderr)

    def test_empty_shell_is_not_a_scorecard(self):
        r = run("--html", self.fixture("empty-shell.html"))
        self.assertEqual(r.returncode, 4)
        self.assertIn("NO_SCORECARD", r.stderr)

    def test_refuses_other_urls(self):
        for bad in ("https://example.com/scorecard/12", "--version;x", "12;rm"):
            r = run(f"--html={self.fixture('no-report.html')}", "--", bad)
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn("BAD_SCORECARD", r.stderr)

    def test_loads_exactly_one_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "calls.log")
            fake = os.path.join(tmp, "fake-chrome")
            with open(fake, "w") as f:
                f.write(f'#!/bin/sh\necho "$@" >> "{log}"\ncat "{self.fixture("no-report.html")}"\n')
            os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
            env = dict(os.environ, CHROME_PATH=fake)
            r = subprocess.run([sys.executable, SCRIPT, "12345"], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(log) as f:
                calls = f.read().strip().split("\n")
        self.assertEqual(len(calls), 1)
        self.assertIn("https://www.cricbay.com/scorecard/12345", calls[0])

    def test_samples_ship_with_the_skill(self):
        path = os.path.join(SCRIPTS, "..", "assets", "sample-reports.md")
        with open(path) as f:
            self.assertGreaterEqual(f.read().count("\n## "), 3)

    def test_accepts_id_and_url(self):
        self.assertEqual(scorecard.scorecard_id("123"), 123)
        self.assertEqual(scorecard.scorecard_id("https://www.cricbay.com/scorecard/123"), 123)
        self.assertEqual(scorecard.scorecard_id("https://cricbay.com/scorecard/123/"), 123)


if __name__ == "__main__":
    unittest.main()
