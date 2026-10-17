# Australian Nationals qualification and scouting interpretation

Research date: **17 October 2026**. This document is maintained separately from
the generated standings. Re-verify policies and event details before acting.

## What is established

- The [official IQ standings](https://events.vex.com/robot-competitions/vex-iq-competition/standings/skills?country=14&region=759&grade_level=Elementary)
  currently identify **2026–2027: Level Up**, season **203**. The page's embedded
  request is the [public elementary feed](https://events.vex.com/api/seasons/203/skills?post_season=0&grade_level=Elementary).
- The page explains that the published total is the ranked Robot Skills score.
  Coding and driver columns are its components; individual maximum columns are
  separate historical peaks used in tie-breaking, not a new combined score.
- The organiser's [public Australian Nationals admission listing](https://events.humanitix.com/https-events-vex-com-admin-evententities-64587-preview-general-info)
  describes the **2026–2027 Australian National Championships**, with team
  check-in **5 December 2026** and public competition **6–7 December**. It states
  that teams other than VEX U must have qualified and be registered.
  Individual spectator/competitor admission tickets are distinct from a team's
  qualification invitation. This listing does **not** publish a NSW skills cutoff.
- The standings page shows **16 March 2027** as regional/state qualification and
  season-finalization deadlines. These are **not verified Australian Nationals
  invitation deadlines**, especially for a December event.

## What remains unverified

No verified current-season source establishes the following for NSW elementary:

- Number of Australian Nationals places or NSW allocation.
- Which awards at each qualifying event carry an invitation.
- Whether, when and how unfilled places are offered through skills standings.
- Whether skills invitations use NSW or all-Australia standings, which events
  count, what tie-breaks apply at the invitation stage, and the relevant cutoff date.
- Invitations already issued, duplicate-qualification handling, waitlists,
  declined places, or the requested team's registration/qualification status.

Potentially relevant current policy pages were discovered but returned **403**
when researched; their contents were not verified:

- [Event Qualifying Criteria](https://library.globalrobotics.org/hc/en-us/articles/50474731922836-Event-Qualifying-Criteria)
- [Which Awards Qualify Teams at VEX IQ Events](https://library.globalrobotics.org/hc/en-us/articles/52516664213396-Which-Awards-Qualify-Teams-at-VEX-IQ-Events)
- [Championship Event Application, Awards and Qualification](https://library.globalrobotics.org/hc/en-us/articles/53675919314580-Championship-Event-Application-Awards-and-Qualification)

Do not apply a past season's policy, infer qualification from the feed's
`eligible` flag, or promise an invitation from a high skills score alone.
Ask the Australian organiser or relevant qualifying event partner to confirm the
current invitation pathway and allocations in writing.

## Target identifier must be confirmed

The captured feed contains **no 2067B in the NSW elementary cohort**.
The expected [2067B profile](https://events.vex.com/teams/VIQRC/2067B) also returned
404 during research. Neither observation proves a zero score or ineligibility.

[2076B](https://events.vex.com/teams/VIQRC/2076B), **Those Guys In The Middle**,
is a distinct verified team. It is not assumed to be the requested team.
Its ranked-result event is the [21 September Knox event](https://events.vex.com/robot-competitions/vex-iq-competition/RE-VIQRC-26-5306.html).
If the number was transposed, confirm that explicitly and regenerate with
`--team 2076B` before using the following conditional comparison.

### Only if 2076B was intended

At the committed capture time:

| Team | NSW position | Total | Coding | Driver | Implication to investigate |
| --- | ---: | ---: | ---: | ---: | --- |
| 21350K | 1 | 138 | 72 | 66 | Leader: coding is 12 above 2076B, driver 6 below |
| 2076B | 2 | 132 | 60 | 72 | Baseline for this conditional comparison only |
| 2076C | 3 | 132 | 48 | 84 | Same total, stronger driver; source tie-break order favors 2076B |
| 21350H | 4 | 126 | 36 | 90 | Lower total but driver 18 above 2076B |
| 2076G | 5 | 114 | 48 | 66 | Both ranked components below 2076B; future gains remain unknown |

**Coding is the first component to investigate against the current leader**:
2076B already has the stronger driver component. Keeping driver at 72 would
require coding **at least 67 mathematically** to exceed 138; check whether the
game's scoring increments permit that exact result. A coding benchmark of
**72**, matching the leader's demonstrated coding component, combined with
2076B's existing driver **72**, would total **144**. This is a proposed practice
benchmark, **not a score 2076B has demonstrated, a guaranteed achievable total,
or a national qualification threshold**.

Validate any gain with repeated full runs at the same event. Observe 2076C and
21350H's driver runs for opportunities, but do not infer mechanisms, routes,
scoring sections or consistency from their totals. A video/run log and the
current game manual are required to make a defensible section-specific plan.

## Before choosing an event or improvement target

1. Confirm the exact team identifier and retrieve its current coding/driver
   baseline; use missing results as unknown, not zero.
2. Confirm the actual entrant list for the next qualifier. NSW geography alone
   does not prove attendance, and interstate entrants may affect invitations.
3. Obtain the event's qualifying-award allocations and any skills-backfill rules.
   Distinguish Robot Skills from Teamwork Challenge and judged awards.
4. Refresh the standings after new results. Use component gaps as training
   hypotheses, then select reliable improvements from observed runs.
5. Check invitation and registration status directly. No numerical national
   cutoff is asserted by this repository.
