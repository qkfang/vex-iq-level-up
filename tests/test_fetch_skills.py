import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import fetch_skills as skills


SEASON = "VEX IQ Robotics Competition 2026-2027: Level Up"


def entry(number="2067B", rank=2, coding=20, driver=30, **team_fields):
    team = {
        "team": number, "teamName": "Test team", "organization": "Test school",
        "city": "Sydney", "country": "Australia", "region": "New South Wales",
        "gradeLevel": "Elementary", "program": "VIQRC",
    }
    team.update(team_fields)
    return {
        "rank": rank,
        "team": team,
        "event": {"sku": "TEST-EVENT", "startDate": "2026-10-01", "seasonName": SEASON},
        "scores": {
            "score": coding + driver, "programming": coding, "driver": driver,
            "maxProgramming": coding, "maxDriver": driver,
        },
        "eligible": True,
    }


class SkillsTests(unittest.TestCase):
    def capture(self, rows):
        return skills.capture(rows, 203, SEASON, "https://events.vex.com/api/seasons/203/skills")

    def test_current_season_is_discovered_not_guessed_from_date(self):
        page = f'Standings for the <i>{SEASON}</i> var url="/api/seasons/203/skills";'
        self.assertEqual(skills.discover_season(page), (203, SEASON))
        with self.assertRaises(ValueError):
            skills.discover_season("<title>Just a moment...</title>")
        with self.assertRaises(ValueError):
            skills.discover_season(page + "/api/seasons/999/skills")

    def test_filters_country_and_state_and_preserves_official_order(self):
        rows = [
            entry(), entry("1A", 1, region="NSW"),
            entry("2A", 3, region="Victoria"),
            entry("3A", 4, country="United States", region="NSW"),
        ]
        data = self.capture(rows)
        self.assertEqual([r["team"]["team"] for r in data["teams"]], ["1A", "2067B"])
        self.assertEqual(data["world_elementary_count"], 4)
        self.assertEqual(data["australia_elementary_count"], 3)

    def test_nullable_region_is_not_assumed_to_be_nsw(self):
        data = self.capture([entry(), entry("1A", 1, region=None)])
        self.assertEqual(len(data["teams"]), 1)
        self.assertEqual(data["teams"][0]["team"]["team"], "2067B")

    def test_rejects_other_grades_programs_duplicates_and_bad_schema(self):
        for rows in (
            [entry(gradeLevel="Middle School")],
            [entry(program="V5RC")],
            [entry(), entry()],
            {"data": []},
            [None],
        ):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.capture(rows)

    def test_rejects_invalid_or_inconsistent_scores(self):
        for field, value in (("score", 100), ("programming", -1),
                             ("driver", "30"), ("maxDriver", 1), ("score", True)):
            row = entry()
            row["scores"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.capture([row])

    def test_rejects_mixed_or_mislabeled_seasons(self):
        row = entry("1A")
        row["event"]["seasonName"] = "Another season"
        with self.assertRaises(ValueError):
            self.capture([entry(), row])
        with self.assertRaises(ValueError):
            self.capture([row])

    def test_maxima_do_not_replace_ranked_total(self):
        own = entry()
        own["scores"]["maxProgramming"] = 80
        data = self.capture([own, entry("1A", 1, coding=40, driver=35)])
        summary, cards = skills.render(data, "2067B")
        self.assertIn("total 50 = coding 20 + driver 30", summary)
        self.assertIn("**76**", summary)
        self.assertIn("**+26**", summary)
        self.assertIn("**coding**", summary)
        self.assertIn("separate maxima exceed", cards)
        self.assertIn("**50**", cards)

    def test_missing_target_not_silently_substituted_or_zeroed(self):
        summary, cards = skills.render(self.capture([entry("2076B")]), "2067B")
        self.assertIn("2067B is absent", summary)
        self.assertIn("2076B", summary)
        self.assertIn("not substituted", summary)
        self.assertIn("n/a", summary)
        self.assertNotIn("Difference versus", cards)
        self.assertNotIn("**+51**", summary)

    def test_tied_total_not_claimed_as_higher(self):
        summary, _ = skills.render(self.capture([entry(), entry("1A", 1)]), "2067B")
        self.assertIn("No NSW team has a strictly higher", summary)
        self.assertNotIn("Nearest strictly higher", summary)

    def test_empty_feed_report_is_explicit(self):
        summary, cards = skills.render(self.capture([]), "2067B")
        self.assertIn("No NSW results", summary)
        self.assertNotIn("NSW published leader", summary)
        self.assertIn("team details", cards)

    def test_untrusted_text_is_escaped(self):
        data = self.capture([entry(teamName="<script>|[link](bad)\n# Heading")])
        summary, cards = skills.render(data, "2067B")
        for text in (summary, cards):
            self.assertNotIn("<script>", text)
            self.assertIn("&lt;script&gt;\\|\\[link\\]", text)

    def test_snapshot_round_trip_and_rejects_out_of_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.json"
            data = self.capture([entry()])
            path.write_text(json.dumps(data))
            self.assertEqual(skills.load_snapshot(path), data)
            invalid = deepcopy(data)
            invalid["teams"][0]["team"]["region"] = "Victoria"
            path.write_text(json.dumps(invalid))
            with self.assertRaises(ValueError):
                skills.load_snapshot(path)

    def test_fetch_failure_does_not_overwrite_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "standings.md"
            report.write_text("previous successful capture")
            with patch.object(skills, "fetch_text", return_value="<html>not JSON</html>"):
                with contextlib.redirect_stderr(io.StringIO()):
                    code = skills.main([
                        "--season-id", "203", "--season-name", SEASON,
                        "--output-dir", directory,
                    ])
            self.assertEqual(code, 1)
            self.assertEqual(report.read_text(), "previous successful capture")

    def test_live_capture_and_offline_regeneration_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "capture.json"
            options = ["--output-dir", str(root / "reports")]
            with patch.object(skills, "fetch_text", return_value=json.dumps([entry()])):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = skills.main(options + [
                        "--season-id", "203", "--season-name", SEASON,
                        "--data-out", str(path),
                    ])
            self.assertEqual(code, 0)
            expected = (root / "reports" / "standings.md").read_text()
            with patch.object(skills, "fetch_text", side_effect=AssertionError("offline")):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = skills.main(options + ["--snapshot", str(path)])
            self.assertEqual(code, 0)
            self.assertEqual((root / "reports" / "standings.md").read_text(), expected)

    def test_http_error_has_actionable_message(self):
        with patch.object(skills, "urlopen", side_effect=HTTPError(
                skills.PAGE_URL, 403, "Forbidden", {}, None)):
            with self.assertRaisesRegex(ValueError, "Do not bypass access controls"):
                skills.fetch_text(skills.PAGE_URL)


if __name__ == "__main__":
    unittest.main()
