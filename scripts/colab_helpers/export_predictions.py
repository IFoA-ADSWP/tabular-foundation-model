"""Export per-run predictions + ground truth into one tidy parquet.

The pilot writes predictions.npy / ground_truth.npy, but .gitignore excludes
*.npy, so they cannot be committed as evidence. This repackages them into a
single parquet that can be, preserving the ability to recompute metrics
without re-running the expensive arm A.
"""
import glob
import json
import os

import numpy as np
import pandas as pd

rows = []
for run_dir in sorted(glob.glob("/content/tfm/outputs/finetune/pilot/*/*/")):
    meta_p = os.path.join(run_dir, "meta.json")
    pred_p = os.path.join(run_dir, "predictions.npy")
    truth_p = os.path.join(run_dir, "ground_truth.npy")
    if not (os.path.exists(meta_p) and os.path.exists(pred_p) and os.path.exists(truth_p)):
        continue

    meta = json.load(open(meta_p))
    y_prob = np.load(pred_p)
    y_true = np.load(truth_p)
    if len(y_prob) != len(y_true):
        print(f"SKIP length mismatch: {run_dir}")
        continue

    for i, (t, p) in enumerate(zip(y_true, y_prob)):
        rows.append({
            "dataset": meta["dataset"],
            "arm": meta["arm"],
            "row_index": i,
            "y_true": int(t),
            "y_prob": float(p),
        })

df = pd.DataFrame(rows)
out = "/content/tfm/outputs/finetune/pilot/pilot_predictions.parquet"
df.to_parquet(out, index=False)

print("rows:", len(df), "cols:", list(df.columns))
print(df.groupby(["dataset", "arm"]).size().to_string())
print("bytes:", os.path.getsize(out))
