"""Rebuild every number from the frozen raw files. Offline; does not re-pull data.

To re-pull and re-freeze raw data (network + CFBD_API_KEY), run src/pull_data.py
separately. That changes the frozen files and must be logged in DEVIATIONS.md.
"""

import subprocess
import sys

STEPS = [
    ["src/verify_data.py"],
    ["src/build_features.py"],
    ["-m", "pytest", "-q", "tests"],
    ["src/train.py"],
    ["src/replay.py"],
    ["src/team_bias.py", "--model", "gbt", "--treatment", "zero"],
    ["src/team_bias.py", "--model", "gbt", "--treatment", "floor"],
]

for step in STEPS:
    print(f"\n== {' '.join(step)}", flush=True)
    subprocess.run([sys.executable, *step], check=True)
