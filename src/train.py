"""Fit the baseline, linear and challenger models on the training seasons only.

Training seasons: 2014-2023, no 2020. The 2024-2025 holdout is never loaded here.
Every model is fit under both unranked treatments (zero = registered, floor =
sensitivity; see DEVIATIONS.md).

Outputs:
  results/train_metrics.json        leave-one-season-out MAE on training seasons
  results/linear_coefficients.csv   linear model fit on all training seasons
  results/model_spec.json           frozen spec + selection rule, fixed before holdout
  results/models/*.joblib           fitted models (rebuilt, not committed)
  data/processed/oof_predictions.csv  out-of-season predictions for team_bias.py

Model choice is the pre-registered rule, applied once when the holdout is scored:
the challenger replaces the linear model only if its holdout MAE is more than 10%
lower. Nothing here looks at the holdout.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RESULTS = ROOT / "results"

TRAIN_SEASONS = [s for s in range(2014, 2024) if s != 2020]
TREATMENTS = ("zero", "floor")
BASE_FEATURES = ["wins", "losses", "bye", "points_for", "points_against", "margin",
                 "home", "away", "neutral", "losses_above", "week"]
GBT_PARAMS = {"max_iter": 300, "learning_rate": 0.05, "random_state": 0}


def features(treatment):
    return [f"prior_points_{treatment}", f"opp_points_{treatment}"] + BASE_FEATURES


def make_models():
    return {
        "linear": LinearRegression(),
        "gbt": HistGradientBoostingRegressor(**GBT_PARAMS),
    }


def load_training():
    tw = pd.read_csv(TABLE)
    train = tw[tw.season.isin(TRAIN_SEASONS)].reset_index(drop=True)
    assert set(train.season) == set(TRAIN_SEASONS)
    return train


def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def leave_one_season_out(train, treatment):
    X, y = train[features(treatment)], train[f"target_{treatment}"]
    oof = pd.DataFrame(index=train.index)
    oof["baseline"] = 0.0
    for name in make_models():
        oof[name] = np.nan
    for season in TRAIN_SEASONS:
        test = train.season == season
        for name, model in make_models().items():
            model.fit(X[~test], y[~test])
            oof.loc[test, name] = model.predict(X[test])
    by_season = {
        int(s): {m: mae(y[train.season == s], oof.loc[train.season == s, m]) for m in oof}
        for s in TRAIN_SEASONS
    }
    overall = {m: mae(y, oof[m]) for m in oof}
    ranked = train.prior_rank.notna()
    ranked_mae = {m: mae(y[ranked], oof.loc[ranked, m]) for m in oof}
    return oof, {"overall": overall, "ranked_teams_only": ranked_mae, "by_season": by_season}


def main():
    train = load_training()
    (RESULTS / "models").mkdir(parents=True, exist_ok=True)
    metrics, coefs, oof_all = {}, [], []

    for tr in TREATMENTS:
        oof, m = leave_one_season_out(train, tr)
        metrics[tr] = m
        keep = ["season", "week", "team", "conference", "conf_group", "prior_rank",
                "next_rank", "wins", "losses", "bye", "margin", f"opp_points_{tr}",
                f"prior_points_{tr}", f"target_{tr}"]
        o = train[keep].rename(columns=lambda c: c.replace(f"_{tr}", ""))
        o["treatment"] = tr
        for name in ("linear", "gbt"):
            o[f"pred_{name}"] = oof[name]
        oof_all.append(o)

        X, y = train[features(tr)], train[f"target_{tr}"]
        for name, model in make_models().items():
            model.fit(X, y)
            joblib.dump(model, RESULTS / "models" / f"{name}_{tr}.joblib")
            if name == "linear":
                coefs.append(pd.DataFrame({
                    "treatment": tr,
                    "term": ["intercept"] + [f.replace(f"_{tr}", "") for f in features(tr)],
                    "coefficient": np.r_[model.intercept_, model.coef_].round(4)}))

    metrics["note"] = ("Leave-one-season-out MAE on training seasons only "
                       "(poll points per team-week). Holdout not used.")
    (RESULTS / "train_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    pd.concat(coefs).to_csv(RESULTS / "linear_coefficients.csv", index=False)
    pd.concat(oof_all).to_csv(ROOT / "data" / "processed" / "oof_predictions.csv", index=False)

    spec = {
        "train_seasons": TRAIN_SEASONS,
        "holdout_seasons": [2024, 2025],
        "target": "target_<treatment> (change in AP points, poll w to w+1)",
        "features": {tr: features(tr) for tr in TREATMENTS},
        "models": {
            "baseline": "predict 0 change",
            "linear": "sklearn LinearRegression, default settings",
            "gbt": {"class": "sklearn HistGradientBoostingRegressor", "params": GBT_PARAMS},
        },
        "selection_rule": ("Use linear unless gbt holdout MAE < 0.9 x linear holdout MAE. "
                           "Applied once, per treatment, when the holdout is scored."),
        "pass_criteria": ("Chosen model beats baseline on holdout MAE, and its predicted "
                          "end-of-season top 25 has Spearman >= 0.7 with the real 2024 "
                          "and 2025 final polls."),
        "collinearity_note": ("margin = points_for - points_against, home + away + neutral = "
                              "wins + losses = games, bye = (games == 0). Predictions are "
                              "unaffected; individual linear coefficients within these "
                              "groups are not separately identifiable."),
    }
    (RESULTS / "model_spec.json").write_text(json.dumps(spec, indent=2) + "\n")

    for tr in TREATMENTS:
        o = metrics[tr]["overall"]
        r = metrics[tr]["ranked_teams_only"]
        print(f"[{tr}] LOSO MAE all: " + ", ".join(f"{k} {v:.1f}" for k, v in o.items())
              + " | ranked only: " + ", ".join(f"{k} {v:.1f}" for k, v in r.items()))


if __name__ == "__main__":
    main()
