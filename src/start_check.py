"""Post hoc: is the T8 premium a skewed preseason start that every conference keeps?
(DEVIATIONS.md, 2026-11-05.) Writes results/t8_start_check.json."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from committee_common import frames  # noqa: E402
from matched_posthoc import POWER, brief, pairs, season_stat  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "t8_start_check.json"


def main():
    allw = frames()
    out = {"note": "post hoc, descriptive; DEVIATIONS.md 2026-11-05"}
    for g in POWER:
        p = pairs(allw, focal=g)
        out[g] = {"share_started_higher": float(p.preseason_higher.mean()),
                  "pairs": int(len(p)),
                  "premium_if_started_higher": brief(season_stat(p[p.preseason_higher])),
                  "premium_if_not": brief(season_stat(p[~p.preseason_higher])),
                  "three_way": {
                      "started_higher": brief(season_stat(p[p.pre_focal < p.pre_match])),
                      "started_level": brief(season_stat(p[p.pre_focal == p.pre_match])),
                      "started_lower": brief(season_stat(p[p.pre_focal > p.pre_match]))},
                  "share_level": float((p.pre_focal == p.pre_match).mean()),
                  "share_lower": float((p.pre_focal > p.pre_match).mean())}
        t = out[g]["three_way"]
        print(f"   three-way: higher {t['started_higher']['mean']:+.2f} | level {t['started_level']['mean']:+.2f} "
              f"(n={t['started_level']['pairs']}) | lower {t['started_lower']['mean']:+.2f} "
              f"(n={t['started_lower']['pairs']}); shares level {out[g]['share_level']:.0%}, lower {out[g]['share_lower']:.0%}")
        a, b, c = out[g]["share_started_higher"], out[g]["premium_if_started_higher"], out[g]["premium_if_not"]
        print(f"{g:8s} started higher {a:5.0%} | premium if higher {b['mean']:+.2f} "
              f"({b['ci95_t'][0]:+.2f} to {b['ci95_t'][1]:+.2f}) | if not {c['mean']:+.2f} "
              f"({c['ci95_t'][0]:+.2f} to {c['ci95_t'][1]:+.2f})")
    OUT.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
