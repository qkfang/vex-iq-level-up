# vex-iq-level-up

NSW elementary VEX IQ skills scouting for **2067B**, using the public JSON feed
behind the official [World Skills Standings](https://events.vex.com/robot-competitions/vex-iq-competition/standings/skills?country=14&region=759&grade_level=Elementary).
The supplied URL's malformed `®ion` parameter is corrected; NSW is region **759**,
not `*` (all states). No API key, third-party package or browser automation is needed.

## Current findings

The **17 October 2026** capture covers **67 NSW elementary teams** in
**2026–2027: Level Up** (season ID **203**).

- **2067B is not listed.** Confirm its number and current-season result before
  drawing conclusions about its performance.
- **2076B** is a different listed identifier: NSW position **2**, total **132**
  (coding **60**, driver **72**). It is not silently substituted for 2067B.
- **21350K** leads the published NSW cohort with **138** (coding **72**, driver **66**).
- Exceeding 138 requires at least **139 mathematically**, but an achievable game
  score must be checked against the manual. This is **not a Nationals cutoff**.

Read [standings and priorities](reports/standings.md),
[every team's details](reports/teams.md), and
[qualification evidence and unknowns](reports/qualification.md).
Scores indicate component balance, not actual robot design, scoring routes or
event attendance. Teams without published skills results are not included.

## Fetch and regenerate

Requires Python **3.10+** (standard library only). Paths below use this checkout.

Discover the current season from the official IQ standings page, then fetch its
complete elementary feed and filter by team location:

```sh
python /home/runner/work/vex-iq-level-up/vex-iq-level-up/scripts/fetch_skills.py
```

Some environments receive a Cloudflare access challenge on the HTML page. The
script stops explicitly; it does not bypass access controls or guess a season.
When the public JSON endpoint is accessible, supply the season ID and official
name verified on the standings page:

```sh
python /home/runner/work/vex-iq-level-up/vex-iq-level-up/scripts/fetch_skills.py \
  --season-id 203 \
  --season-name 'VEX IQ Robotics Competition 2026-2027: Level Up'
```

**203 is the verified October 2026 season, not a permanent “current season”
default.** Re-check the standings when seasons change. The script validates
season names against returned results, rejects mixed seasons or unexpected
schemas, and does not overwrite reports following a fetch/validation failure.
An empty valid feed produces an explicitly empty report, not invented scores.

The public endpoint is undocumented:
`https://events.vex.com/api/seasons/{season_id}/skills?post_season=0&grade_level=Elementary`.
It returns the full array, not a paginated API response. Filtering is local:
country `Australia`, state `NSW` or `New South Wales`, grade `Elementary`, and IQ
program. Missing state information is not assumed to mean NSW.

Outputs:

- `data/nsw-skills.json`: timestamped metadata and original NSW rows only.
- `reports/standings.md`: cohort table, target gaps, priorities and limitations.
- `reports/teams.md`: each team's ranked score components, separate maxima,
  organization, city, event SKU/date, profile link and scouting questions.
- `reports/qualification.md`: separately maintained qualification research; not
  overwritten by the script.

Reproduce the committed reports offline without changing their capture time:

```sh
python /home/runner/work/vex-iq-level-up/vex-iq-level-up/scripts/fetch_skills.py \
  --snapshot /home/runner/work/vex-iq-level-up/vex-iq-level-up/data/nsw-skills.json
```

If **2076B** is confirmed as the intended target, generate a separate comparison
without replacing the original 2067B reports:

```sh
python /home/runner/work/vex-iq-level-up/vex-iq-level-up/scripts/fetch_skills.py \
  --snapshot /home/runner/work/vex-iq-level-up/vex-iq-level-up/data/nsw-skills.json \
  --team 2076B --output-dir /tmp/vex-2076B
```

Use `--data-out` and `--output-dir` to retain separate dated captures rather than
overwriting defaults. Refresh after relevant events; older captures cannot
predict future competitors or scores. A missing target emits a warning but
still successfully generates the cohort reports.

## Score interpretation

Use the published `score = programming + driver` result. Separate
`maxProgramming` and `maxDriver` values may come from different events: adding
them is not a valid replacement for the ranked score. NSW positions preserve
the feed's official world order, including its tie-break ordering; they are
derived positions, not official NSW qualification ranks.

When the target exists, the report compares it with every NSW team and identifies
positive component gaps to the nearest strictly stronger total. This suggests
where to investigate, not a guaranteed training outcome. Actual scoring-section
recommendations require run/video observations and the current game manual.
The `eligible` field is retained in the raw capture but never interpreted as
Australian Nationals qualification.

## Tests

```sh
cd /home/runner/work/vex-iq-level-up/vex-iq-level-up
python -m unittest discover -s /home/runner/work/vex-iq-level-up/vex-iq-level-up/tests -v
```

Tests use synthetic fixtures and mocked networking; no credentials or live
network requests are needed. There is no separate build or lint configuration.