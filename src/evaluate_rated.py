"""2024-2025 numbers for the rated spec. NOT a clean holdout: those seasons were
already scored for the registered and revised specs (results/holdout.json) before
the rated spec existed. Reported as "holdout re-used" (DEVIATIONS.md, 2026-10-23).
"""

import json
from pathlib import Path

import pandas as pd

from score_holdout import score
from train import TREATMENTS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "holdout_reuse_rated.json"


def main():
    tw = pd.read_csv(ROOT / "data" / "processed" / "team_weeks.csv")
    report = {f"rated_{t}": score(tw, "rated", t) for t in TREATMENTS}
    report["note"] = ("Holdout re-used: 2024-2025 had already been scored for other specs "
                      "before this spec was defined. Not a clean out-of-sample test.")
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    for t in TREATMENTS:
        r = report[f"rated_{t}"]
        sp = {s: round(r["replay"][s]["final_regular"]["spearman"], 2) for s in r["replay"]}
        st = {s: round(r["replay"][s]["stickiness"]["spots_kept_above_real"], 2) for s in r["replay"]}
        print(f"[rated_{t}] MAE baseline {r['mae']['baseline']:.2f}, linear {r['mae']['linear']:.2f}, "
              f"gbt {r['mae']['gbt']:.2f} -> {r['chosen_model']}; replay Spearman {sp}; "
              f"stickiness {st}; {'PASS' if r['pass']['passed'] else 'FAIL'}")


if __name__ == "__main__":
    main()
