"""Prepare CASdatasets .rda files as clean CSVs for the TabArena insurance benchmark.

Reads .rda files (default data/raw_sources/, pass SRC_DIR to override) and
writes cleaned CSVs to data/raw/. Categorical columns are written as strings;
binary targets are int.
The Spanish motor portfolio source is a raw CSV (comma-separated, "NA" convention,
DD/MM/YYYY dates) — handled by a CSV-source branch in main().

Usage:
    python scripts/infra/prepare_insurance_datasets.py [SRC_DIR]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadr

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent  # repo root (this file lives in scripts/infra/)
OUT_DIR = REPO / "data" / "raw"
SRC_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "data" / "raw_sources"

# Spanish motor portfolio: source is a raw CSV, not an .rda (see module docstring).
SPANISH_MOTOR_CSV = (
    REPO / "data" / "raw" / "Spanish motor portfolio" / "Motor vehicle insurance data.csv"
)
CSV_SOURCES = {"spanish_motor": SPANISH_MOTOR_CSV}

_SPANISH_NUM = [
    "Lapse", "N_claims_year", "Cost_claims_year", "N_claims_history", "R_Claims_history",
    "Seniority", "Policies_in_force", "Max_policies", "Max_products", "Payment", "Premium",
    "Power", "Cylinder_capacity", "Value_vehicle", "N_doors", "Length", "Weight",
    "Year_matriculation", "Second_driver", "Distribution_channel", "Type_risk", "Area",
]

# Shared feature set for both spanish_motor variants (step-1 validation: raw date
# columns, ID and Date_lapse are dropped; Date_lapse presence achieves AUC ~0.85 vs
# lapse — termination-date variable, must-exclude per the bemtl97 leak rule).
_SPANISH_FEATURES = [
    "Distribution_channel", "Seniority", "Policies_in_force", "Max_policies", "Max_products",
    "Payment", "Premium", "Type_risk", "Area", "Second_driver", "driver_age", "licence_age",
    "vehicle_age", "Power", "Cylinder_capacity", "Value_vehicle", "N_doors", "Type_fuel",
    "Length", "Weight",
]


def _to_str(df: pd.DataFrame, cols: list[str]) -> None:
    for c in cols:
        df[c] = df[c].astype(str)


def make_uslapseagent(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    keep = ["duration", "acc.death.rider", "gender", "premium.frequency", "risk.state",
            "underwriting.age", "living.place", "annual.premium", "DJIA",
            "surrender", "allcause"]
    cats = ["acc.death.rider", "gender", "premium.frequency", "risk.state",
            "underwriting.age", "living.place"]
    df = df[keep].copy()
    df["surrender"] = df["surrender"].astype(int)
    df["allcause"] = df["allcause"].astype(int)
    _to_str(df, cats)
    return df, ["surrender", "allcause", "duration"]


def make_bemtl97(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    keep = ["expo", "coverage", "ageph", "sex", "bm", "power", "agec", "fuel",
            "use", "fleet", "claim", "nclaims", "amount"]
    cats = ["coverage", "sex", "fuel", "use"]
    df = df[keep].copy()
    df["claim"] = df["claim"].astype(int)
    df["fleet"] = df["fleet"].astype(int)
    df["amount"] = np.log1p(df["amount"].fillna(0.0))
    _to_str(df, cats)
    return df, ["claim", "nclaims", "amount"]


def make_bemtl16(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    keep = ["policy_year", "exposure", "insured_birth_year", "vehicle_age",
            "policy_holder_age", "driver_license_age", "vehicle_brand",
            "vehicle_model", "mileage", "vehicle_power", "catalog_value",
            "claim_responsibility_rate", "driving_training_label",
            "number_of_liability_claims"]
    cats = ["vehicle_brand", "vehicle_model", "driving_training_label"]
    # Panel data: one row per policy-year; keep the latest year per contract.
    df = (df.sort_values("policy_year")
            .groupby("insurance_contract", as_index=False).tail(1))[keep]
    df["number_of_liability_claims"] = df["number_of_liability_claims"].astype(int)
    _to_str(df, cats)
    return df, ["number_of_liability_claims"]


def make_ausauto(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    keep = ["AccMth", "ReportMth", "FinMth", "OpTime", "InjType1", "InjType2",
            "InjType3", "InjType4", "InjType5", "InjNb", "Legal", "AggClaim"]
    cats = ["InjType1", "InjType2", "InjType3", "InjType4", "InjType5", "Legal"]
    df = df[keep].copy()
    df["AggClaim"] = np.log(df["AggClaim"])
    _to_str(df, cats)
    return df, ["AggClaim"]


def make_norauto(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    keep = ["Male", "Young", "DistLimit", "GeoRegion", "Expo", "NbClaim"]
    cats = ["DistLimit", "GeoRegion"]
    df = df[keep].copy()
    # Binarise claim count -> has-claim (4.6% positive)
    df["NbClaim"] = (df["NbClaim"] > 0).astype(int)
    _to_str(df, cats)
    return df, ["NbClaim"]


def _spanish_motor_base(df: pd.DataFrame) -> pd.DataFrame:
    """Shared transform for both spanish_motor makers: coerce numerics, collapse the
    policy-year panel to the LAST row per ID (bemtl16 precedent — avoids same-policy
    rows leaking across random folds), derive ages from the DD/MM/YYYY dates, and
    impute the motorbike NA trap. Length NA is ~100% Type_risk==1 (motorbikes) —
    the frontier harness fillna(0) would set bike length to 0.0 m, so impute median
    by Type_risk here; Type_fuel NA -> 'unknown' category (N_doors==0 is genuine
    motorbike data, NOT missing — untouched)."""
    for c in _SPANISH_NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    last = pd.to_datetime(df["Date_last_renewal"], format="%d/%m/%Y")
    df = (df.assign(_last=last)
            .sort_values(["ID", "_last"])
            .groupby("ID", as_index=False)
            .tail(1)
            .drop(columns=["_last"]))
    last = pd.to_datetime(df["Date_last_renewal"], format="%d/%m/%Y")
    df["driver_age"] = (last - pd.to_datetime(df["Date_birth"], format="%d/%m/%Y")).dt.days / 365.25
    df["licence_age"] = (last - pd.to_datetime(df["Date_driving_licence"], format="%d/%m/%Y")).dt.days / 365.25
    df["vehicle_age"] = last.dt.year - df["Year_matriculation"]
    df["Length"] = df.groupby("Type_risk")["Length"].transform(lambda s: s.fillna(s.median()))
    df["Type_fuel"] = df["Type_fuel"].fillna("unknown").astype(str)
    return df


def make_spanish_motor_freq(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Claims-frequency variant (frontier regression mode, poisson_deviance). Target:
    N_claims_year (int count, 0-25). Leak exclusions verified in step 1:
    N_claims_history / R_Claims_history include CURRENT-year claims (AUC 0.76/0.92 vs
    claims>0; hist==0 => current==0 with zero exceptions) and Cost_claims_year is a
    sibling target (cost==0 iff N==0 exactly) — none are kept as features."""
    keep = _SPANISH_FEATURES + ["N_claims_year"]
    out = _spanish_motor_base(df)[keep].copy()
    out["N_claims_year"] = out["N_claims_year"].astype(int)
    return out, ["N_claims_year"]


def make_spanish_motor_lapse(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Lapse variant (frontier classification mode). Target: LapseB = (Lapse > 0),
    binarised from the stored count 0-7 (dictionary: book-level cancellations per
    maturity year). Current-year claims ARE kept as features (AUC ~0.54 vs lapse —
    verified non-leak). Date_lapse is excluded (presence AUC 0.85 vs lapse)."""
    base = _spanish_motor_base(df)
    keep = _SPANISH_FEATURES + ["N_claims_year", "Cost_claims_year"]
    out = base[keep].copy()
    out["LapseB"] = (base["Lapse"] > 0).astype(int)
    return out, ["LapseB"]


def make_spanish_motor_severity(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Severity variant (frontier regression mode, rmse). Target: log1p-transformed
    Cost_claims_year in place (bemtl97_amount precedent: log1p zero-inflated target,
    RMSE on the stored log-scale). Same leak exclusions as the freq variant
    (N_claims_history / R_Claims_history include current-year claims) PLUS
    N_claims_year: cost==0 iff N_claims_year==0 exactly, so the count would hand the
    model the zero/non-zero split of the target for free (sibling target family)."""
    base = _spanish_motor_base(df)
    out = base[_SPANISH_FEATURES].copy()
    out["Cost_claims_year"] = np.log1p(base["Cost_claims_year"])
    return out, ["Cost_claims_year"]


DATASETS = [
    ("uslapseagent", "uslapseagent.csv", make_uslapseagent),
    ("beMTPL97", "bemtl97.csv", make_bemtl97),
    ("beMTPL16", "bemtl16.csv", make_bemtl16),
    ("ausautoBI8999", "ausautoBI8999.csv", make_ausauto),
    ("norauto", "norauto.csv", make_norauto),
    ("spanish_motor", "spanish_motor_freq.csv", make_spanish_motor_freq),
    ("spanish_motor", "spanish_motor_lapse.csv", make_spanish_motor_lapse),
    ("spanish_motor", "spanish_motor_severity.csv", make_spanish_motor_severity),
]


def _print_stats(df: pd.DataFrame, targets: list[str]) -> None:
    for t in targets:
        s = df[t]
        n = len(s)
        if s.dtype.kind in "iu" and s.nunique() <= 2:
            pos = int((s == 1).sum())
            print(f"      target {t}: binary, positive rate {pos}/{n} = {pos / n:.1%}")
        else:
            print(f"      target {t}: numeric, min {s.min():.4g} mean {s.mean():.4g} max {s.max():.4g}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    for stem, out_name, maker in DATASETS:
        if only is not None and stem != only:
            continue
        if stem in CSV_SOURCES:
            # CSV-source branch: Spanish motor portfolio (comma-sep, "NA" convention,
            # DD/MM/YYYY dates parsed in the maker). Existing datasets keep the .rda path.
            df_raw = pd.read_csv(CSV_SOURCES[stem], sep=",", na_values=["NA", "na"])
        else:
            src = SRC_DIR / f"{stem}.rda"
            df_raw = list(pyreadr.read_r(src).values())[0]
        df, targets = maker(df_raw)
        out = OUT_DIR / out_name
        df.to_csv(out, index=False)
        print(f"{out.name}: {df.shape[0]} rows x {df.shape[1]} cols")
        _print_stats(df, targets)
        if stem == "spanish_motor":
            t = df[targets[0]]
            rate = (t == 1).mean() if t.nunique() == 2 else (t > 0).mean()
            print(f"      spanish_motor {out_name}: {rate:.1%} positive/claims>0 rate")


if __name__ == "__main__":
    main()
