"""Rebuild every number from the frozen raw files.

The first step, src/fetch_data.py, downloads any raw file that is missing and checks
every file against data/MANIFEST.json (polls need a free CFBD_API_KEY). With the files
already present, the whole run is offline.

To re-pull and re-freeze raw data, run src/pull_data.py separately. That changes the
frozen files and must be logged in DEVIATIONS.md.
"""

import os
import subprocess
import sys

# One thread everywhere, so results do not depend on the machine (DEVIATIONS.md).
ENV = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")

STEPS = [
    ["src/fetch_data.py"],
    ["src/verify_data.py"],
    ["src/season_rating.py"],
    ["src/build_features.py"],
    ["-m", "pytest", "-q", "tests"],
    ["src/train.py"],
    ["src/replay.py"],
    ["src/score_holdout.py"],
    ["src/evaluate_rated.py"],
    ["src/counterfactual.py", "revised"],
    ["src/counterfactual.py", "rated"],
    ["src/base_rates.py"],
    ["src/hypothesis.py"],
    ["src/bias_tests.py"],
    ["src/h5_sensitivity.py"],
    ["src/rankings_2026.py"],
    ["src/preseason_tests.py"],
    ["src/team_bias.py", "--spec", "revised", "--model", "gbt", "--treatment", "zero"],
    ["src/team_bias.py", "--spec", "revised", "--model", "gbt", "--treatment", "floor"],
    ["src/figures.py"],
]

for step in STEPS:
    print(f"\n== {' '.join(step)}", flush=True)
    subprocess.run([sys.executable, *step], check=True, env=ENV)
