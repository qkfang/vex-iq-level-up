#!/usr/bin/env python3
"""Fetch the public VEX IQ skills feed and report on NSW elementary teams."""

import argparse
from datetime import datetime, timezone
import difflib
import html
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://events.vex.com"
STANDINGS = ORIGIN + "/robot-competitions/vex-iq-competition/standings/skills"
PAGE_URL = STANDINGS + "?" + urlencode(
    {"country": 14, "region": 759, "grade_level": "Elementary"}
)
SCORE_FIELDS = ("score", "programming", "driver", "maxProgramming", "maxDriver")


def fetch_text(url):
    request = Request(url, headers={
        "Accept": "application/json, text/html",
        "User-Agent": "vex-iq-level-up/1.0 (public skills scouting)",
    })
    try:
        with urlopen(request, timeout=60) as response:
            text = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ValueError(
            f"Could not fetch {url}: {exc}. Do not bypass access controls. "
            "If season discovery is blocked, supply --season-id and --season-name "
            "from the official standings page; use --snapshot for a saved capture."
        ) from exc
    if "Just a moment..." in text:
        raise ValueError("VEX returned an access challenge, not standings data.")
    return text


def discover_season(page):
    ids = set(re.findall(r"/api/seasons/(\d+)/skills", page))
    name = re.search(r"Standings for the\s*<i>(.*?)</i>", page, re.DOTALL)
    if len(ids) != 1 or name is None:
        raise ValueError(
            "Cannot discover the current IQ season. Supply --season-id and "
            "--season-name verified on the official standings page."
        )
    return int(ids.pop()), html.unescape(re.sub(r"<[^>]+>", "", name[1])).strip()


def integer(value, field):
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer.")
    return value


def validate_rows(rows):
    if not isinstance(rows, list):
        raise ValueError("Expected the complete public skills feed as a JSON array.")
    seen = set()
    seasons = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid skills row.")
        team, event, scores = (row.get(key) for key in ("team", "event", "scores"))
        if not all(isinstance(item, dict) for item in (team, event, scores)):
            raise ValueError("Skills row must contain team, event and scores objects.")
        for key in ("team", "teamName", "organization", "city", "region",
                    "country", "gradeLevel", "program"):
            if key == "region" and key in team and team[key] is None:
                continue
            if not isinstance(team.get(key), str):
                raise ValueError(f"Missing or invalid team.{key}.")
        number = team["team"].upper()
        if not re.fullmatch(r"[0-9]+[A-Z]+", number) or number in seen:
            raise ValueError(f"Invalid or duplicate team identifier: {number}")
        seen.add(number)
        if team["gradeLevel"] != "Elementary" or team["program"] not in ("VIQRC", "VIQC"):
            raise ValueError("Feed is not exclusively VEX IQ Elementary.")
        if integer(row.get("rank"), "rank") == 0:
            raise ValueError("Source rank must be positive.")
        for key in SCORE_FIELDS:
            integer(scores.get(key), f"scores.{key}")
        if scores["score"] != scores["programming"] + scores["driver"]:
            raise ValueError(f"{number}: combined score does not equal its components.")
        if (scores["maxProgramming"] < scores["programming"]
                or scores["maxDriver"] < scores["driver"]):
            raise ValueError(f"{number}: individual maximum is below ranked component.")
        for key in ("sku", "startDate", "seasonName"):
            if not isinstance(event.get(key), str) or not event[key]:
                raise ValueError(f"Missing event.{key}.")
        seasons.add(event["seasonName"])
    if len(seasons) > 1:
        raise ValueError("Mixed seasons in feed; refusing a misleading comparison.")
    return sorted(rows, key=lambda row: row["rank"])


def is_nsw(row):
    team = row["team"]
    return (team["country"].strip().casefold() == "australia"
            and (team["region"] or "").strip().casefold() in ("nsw", "new south wales"))


def capture(rows, season_id, season_name, source_url):
    rows = validate_rows(rows)
    for row in rows:
        if row["event"]["seasonName"] not in season_name:
            raise ValueError("Season name disagrees with the feed; check --season-name.")
    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "season_id": season_id,
        "season_name": season_name,
        "source_url": source_url,
        "standings_url": PAGE_URL,
        "scope": "Australia / New South Wales / Elementary / VEX IQ",
        "world_elementary_count": len(rows),
        "australia_elementary_count": sum(
            row["team"]["country"].strip().casefold() == "australia" for row in rows
        ),
        "teams": [row for row in rows if is_nsw(row)],
    }


def load_snapshot(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported snapshot; use a capture produced by this script.")
    for key in ("captured_at", "season_name", "source_url", "standings_url", "scope"):
        if not isinstance(data.get(key), str) or not data[key]:
            raise ValueError(f"Snapshot is missing {key}.")
    integer(data.get("season_id"), "season_id")
    data["teams"] = validate_rows(data.get("teams"))
    if not all(is_nsw(row) for row in data["teams"]):
        raise ValueError("Snapshot contains teams outside NSW.")
    for row in data["teams"]:
        if row["event"]["seasonName"] not in data["season_name"]:
            raise ValueError("Snapshot season name disagrees with its team data.")
    return data


def md(value):
    text = html.escape(str(value), quote=False)
    for char in ("\\", "|", "[", "]", "*", "_", "`"):
        text = text.replace(char, "\\" + char)
    return " ".join(text.split())


def profile(number):
    return f"{ORIGIN}/teams/VIQRC/{number}"


def score_style(scores):
    coding, driver = scores["programming"], scores["driver"]
    if coding == driver == 0:
        return "No scored capability demonstrated"
    if coding == 0:
        return "Driver-only ranked result; coding is an unproven scoring opportunity"
    if driver == 0:
        return "Coding-only ranked result; driver is an unproven scoring opportunity"
    if coding > driver:
        return "Coding-led score profile"
    if driver > coding:
        return "Driver-led score profile"
    return "Equal coding and driver contribution"


def render(data, target):
    rows = data["teams"]
    own = next((r for r in rows if r["team"]["team"].upper() == target), None)
    lines = [
        f"# NSW elementary skills scouting — {md(target)}",
        "",
        f"- Season: **{md(data['season_name'])}** (ID {data['season_id']}).",
        f"- Captured (UTC): {md(data['captured_at'])}. This is a dated snapshot, not live data.",
        f"- Scope: {len(rows)} NSW elementary teams with a published skills result.",
        "- Teams without published results are not represented; this is not a registration roster.",
        "- NSW position below is derived from the official feed order, not an official "
        "NSW qualification ranking. Equal totals retain source tie-break order.",
        "- Every listed team is a possible competitor, not a confirmed attendee at "
        f"{target}'s next event. Event entries and qualification status need separate verification.",
        "",
        "## Target and improvement priorities",
        "",
    ]
    if own:
        scores = own["scores"]
        position = rows.index(own) + 1
        lines += [
            f"**{target}: NSW position {position}/{len(rows)}, source world elementary "
            f"rank {own['rank']}, total {scores['score']} "
            f"= coding {scores['programming']} + driver {scores['driver']}.**",
            "",
        ]
        stronger = [r for r in rows if r["scores"]["score"] > scores["score"]]
        if stronger:
            peer = stronger[-1]
            peer_scores = peer["scores"]
            coding_gap = max(0, peer_scores["programming"] - scores["programming"])
            driver_gap = max(0, peer_scores["driver"] - scores["driver"])
            priority = ("coding" if coding_gap > driver_gap else "driver"
                        if driver_gap > coding_gap else "both components equally")
            lines += [
                f"Nearest strictly higher total: **{peer['team']['team']}** "
                f"({peer_scores['score']}). Prioritize **{priority}** for investigation: "
                f"positive component gaps are coding {coding_gap}, driver {driver_gap}.",
                f"A total of **{peer_scores['score'] + 1}** would exceed that published "
                f"total: **+{peer_scores['score'] + 1 - scores['score']}** points. "
                "This is an arithmetic lower bound, not a validated achievable game score.",
                f"Holding driver at {scores['driver']}, coding would need at least "
                f"{peer_scores['score'] + 1 - scores['driver']}; holding coding at "
                f"{scores['programming']}, driver would need at least "
                f"{peer_scores['score'] + 1 - scores['programming']}. "
                "Check feasible scoring increments and reliability before selecting either plan.",
                "",
            ]
        else:
            lines += ["No NSW team has a strictly higher published total; defend the "
                      "lead and check equal-score tie-breaks.", ""]
    else:
        similar = difflib.get_close_matches(
            target, [r["team"]["team"].upper() for r in rows], n=3, cutoff=0.7
        )
        lines += [
            f"**{target} is absent from this NSW elementary skills capture.** Its standing, "
            "score deficit and weakest component cannot be determined. Absence is not a zero "
            "score and does not establish registration or qualification status.",
            f"Similar identifiers (not substituted): {', '.join(similar) if similar else 'none'}. "
            "Confirm the exact team number, grade, state and whether a current-season result "
            "has been posted before setting a team-specific target.",
            "",
        ]
    if rows:
        leader = rows[0]
        total = leader["scores"]["score"]
        lines += [
            f"NSW published leader: **{leader['team']['team']}**, **{total}** "
            f"(coding {leader['scores']['programming']}, driver {leader['scores']['driver']}). "
            f"**{total + 1}** is the arithmetic minimum to exceed every total in this capture, "
            "not a guaranteed achievable score or Nationals invitation threshold.",
            "",
            "Training order:",
            "1. Establish repeatable driver and autonomous baselines at the same event; "
            "ranked components, not the sum of separate all-time maxima, determine the total.",
            "2. Investigate the positive component gaps to the nearest stronger peer, then "
            "the leader. Use repeated practice runs to select the highest reliable points gain.",
            "3. Review match video and the current game manual to identify actual routes, "
            "scoring sections and mechanism changes. Totals alone cannot reveal these.",
            "4. Track median, best and failed runs for each component; reproduce gains under "
            "event conditions rather than relying on one peak run.",
            "",
        ]
    else:
        lines += ["No NSW results in this capture; no leader or score target can be inferred.", ""]
    lines += [
        "## Standings",
        "",
        "Delta is competitor total minus target total; n/a means target is missing.",
        "",
        "| NSW position | World elementary rank | Team | Name | Total | Coding | Driver | "
        "Highest coding | Highest driver | Delta |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for position, row in enumerate(rows, 1):
        t, s = row["team"], row["scores"]
        number = t["team"].upper()
        delta = f"{s['score'] - own['scores']['score']:+d}" if own else "n/a"
        lines.append(
            f"| {position} | {row['rank']} | [{number}]({profile(number)}) | "
            f"{md(t['teamName'])} | {s['score']} | {s['programming']} | {s['driver']} | "
            f"{s['maxProgramming']} | {s['maxDriver']} | {delta} |"
        )
    lines += [
        "",
        "## Nationals: what these scores do not prove",
        "",
        "A NSW skills position does **not** itself award an Australian Nationals ticket. "
        "Verify the current season's Australian event invitation policy, qualifying awards, "
        "spot allocations, eligibility, deadlines and any skills backfill with the organiser. "
        "The feed's `eligible` flag is not treated as a Nationals invitation.",
        "See [qualification research](qualification.md). No fixed qualification cutoff has "
        "been verified, so none is asserted.",
        "",
        "## Sources and interpretation",
        "",
        f"- [Official filtered standings]({PAGE_URL}) (Australia country 14, NSW region 759).",
        f"- Public feed: `{md(data['source_url'])}`.",
        "- The feed is an undocumented public endpoint used by the standings page; schema "
        "changes cause validation errors rather than silently changing calculations.",
        "- Total = ranked coding + ranked driver. Highest coding/driver can come from other "
        "events and must not be added to replace the published total.",
        "- Score profiles are inferences about component balance, not observed robot strategy. "
        "No claim of specific scoring sections, consistency, attendance or future performance "
        "is possible from this feed alone.",
        "",
    ]
    cards = [
        "# NSW elementary team details",
        "",
        f"Season: {md(data['season_name'])}. Captured (UTC): {md(data['captured_at'])}.",
        "All teams with published NSW elementary results are included. "
        "Component deltas compare against the requested target, not separate historical maxima.",
        "",
    ]
    for position, row in enumerate(rows, 1):
        t, s, event = row["team"], row["scores"], row["event"]
        number = t["team"].upper()
        cards += [
            f"## {number} — {md(t['teamName'])}",
            "",
            f"- [Official team profile]({profile(number)}).",
            f"- Organization: {md(t['organization'])}; city: {md(t['city'])}.",
            f"- NSW position: {position}; source world elementary rank: {row['rank']}.",
            f"- Ranked total: **{s['score']}** = coding **{s['programming']}** "
            f"+ driver **{s['driver']}**.",
            f"- Separate component maxima: coding {s['maxProgramming']}; "
            f"driver {s['maxDriver']} (not a combined ranked score).",
            f"- Ranked-result event: `{md(event['sku'])}`; starts {md(event['startDate'])}.",
            f"- Score profile (inference): {score_style(s)}.",
        ]
        if own:
            cards += [
                f"- Difference versus {target}: total "
                f"{s['score'] - own['scores']['score']:+d}; coding "
                f"{s['programming'] - own['scores']['programming']:+d}; driver "
                f"{s['driver'] - own['scores']['driver']:+d}.",
            ]
        if s["maxProgramming"] + s["maxDriver"] > s["score"]:
            cards += ["- Watch item: separate maxima exceed the ranked total; demonstrated "
                      "component peaks suggest potential, not a score the team has posted together."]
        cards += [
            "- Scouting to verify: actual scoring routes/sections, cycle time, autonomous "
            "reliability, next-event entry and invitation status are unknown.",
            "",
        ]
    return "\n".join(lines), "\n".join(cards)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", default="2067B")
    parser.add_argument("--season-id", type=int, help="Explicit season ID verified on the IQ standings page")
    parser.add_argument("--season-name", help="Official season name (required with --season-id)")
    parser.add_argument("--snapshot", type=Path, help="Regenerate offline from an existing capture")
    parser.add_argument("--data-out", type=Path, default=ROOT / "data" / "nsw-skills.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args(argv)
    target = args.team.strip().upper()
    if not re.fullmatch(r"[0-9]+[A-Z]+", target):
        parser.error("--team must be a team identifier such as 2067B")
    if bool(args.season_id is not None) != bool(args.season_name):
        parser.error("--season-id and --season-name must be supplied together")
    if args.snapshot and args.season_id is not None:
        parser.error("--snapshot cannot be combined with season overrides")
    try:
        if args.snapshot:
            data = load_snapshot(args.snapshot)
        else:
            season_id, season_name = (
                (args.season_id, args.season_name) if args.season_id is not None
                else discover_season(fetch_text(PAGE_URL))
            )
            if season_id <= 0:
                raise ValueError("--season-id must be positive.")
            source_url = f"{ORIGIN}/api/seasons/{season_id}/skills?" + urlencode(
                {"post_season": 0, "grade_level": "Elementary"}
            )
            data = capture(json.loads(fetch_text(source_url)), season_id, season_name, source_url)
        summary, teams = render(data, target)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        if not args.snapshot:
            args.data_out.parent.mkdir(parents=True, exist_ok=True)
            args.data_out.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        (args.output_dir / "standings.md").write_text(summary, encoding="utf-8")
        (args.output_dir / "teams.md").write_text(teams, encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {len(data['teams'])} NSW team details to {args.output_dir.resolve()}")
    if not any(r["team"]["team"].upper() == target for r in data["teams"]):
        print(f"Warning: {target} not found; see standings.md before drawing conclusions.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
