"""Finetune pilot: measures per-sample time for the TabPFN fine-tuning loop.

Usage:
    python scripts/legacy_finetuning/finetune_pilot.py --n_pilot 2000 --device cpu
"""
import argparse
import os
import time
import textwrap
import numpy as np
import torch
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

try:
    from tabpfn import TabPFNClassifier
except Exception:
    TabPFNClassifier = None


def synthetic_data(n_samples=2000, n_features=20, n_classes=2, random_state=42):
    X, y = make_classification(n_samples=n_samples, n_features=n_features,
                               n_informative=min(10, n_features), n_redundant=0,
                               n_classes=n_classes, random_state=random_state)
    return X.astype(np.float32), y


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_pilot", type=int, default=2000)
    parser.add_argument("--n_features", type=int, default=20)
    parser.add_argument("--n_classes", type=int, default=2)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--batch_size", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--n_estimators", type=int, default=2)
    parser.add_argument("--hf_token", type=str, default=None)
    args = parser.parse_args()

    if args.hf_token:
        os.environ["HF_TOKEN"] = args.hf_token

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")

    if TabPFNClassifier is None:
        print("TabPFN not installed. Install with: pip install tabpfn")
        return

    print(f"Building synthetic dataset: n={args.n_pilot}, features={args.n_features}")
    X, y = synthetic_data(args.n_pilot, args.n_features, args.n_classes)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    train_n = int(len(X_train))

    finetune_config = {"epochs": args.epochs, "learning_rate": 1e-5, "meta_batch_size": 1}
    batch_size = args.batch_size or min(10000, int(len(X_train)))

    clf = TabPFNClassifier(ignore_pretraining_limits=True, device=device,
                           n_estimators=args.n_estimators, random_state=42,
                           inference_precision=torch.float32, fit_mode="batched",
                           differentiable_input=False)
    try:
        clf._initialize_model_variables()
    except Exception:
        pass

    try:
        from tabpfn.finetuning.data_util import get_preprocessed_dataset_chunks
    except Exception as e:
        print(f"Failed to import finetuning helpers: {e}")
        return

    split_fn = lambda X, y, stratify=None: train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify)
    try:
        training_datasets = get_preprocessed_dataset_chunks(
            calling_instance=clf, X_raw=X_train, y_raw=y_train, split_fn=split_fn,
            max_data_size=None, model_type="classifier", equal_split_size=True,
            data_shuffle_seed=42, preprocessing_random_state=42, shuffle=True,
        )
    except Exception as e:
        print(f"Failed to build preprocessed datasets: {e}")
        return

    from torch.optim import Adam
    from torch.utils.data import DataLoader
    from tabpfn.architectures.interface import PerformanceOptions
    from tabpfn.finetuning.data_util import meta_dataset_collator

    optimizer = Adam(clf.model_.parameters(), lr=finetune_config["learning_rate"]) if hasattr(clf, "model_") else None
    dataloader = DataLoader(training_datasets, batch_size=finetune_config["meta_batch_size"], collate_fn=meta_dataset_collator)
    loss_fn = torch.nn.CrossEntropyLoss()

    total_train_time = 0.0
    print(f"Starting finetune pilot on device={device} batches={len(dataloader)} batch_size(meta)={finetune_config['meta_batch_size']}")

    for epoch in range(finetune_config["epochs"]):
        for batch_item in dataloader:
            X_train_batch = batch_item.X_context
            y_train_batch = batch_item.y_context
            X_test_batch = batch_item.X_query
            y_test_batch = batch_item.y_query
            cat_ixs = batch_item.cat_indices
            confs = batch_item.configs

            start = time.perf_counter()
            try:
                clf.fit_from_preprocessed(X_train_batch, y_train_batch, cat_ixs, confs, performance_options=PerformanceOptions())
            except Exception as e:
                print(f"fit_from_preprocessed failed: {e}")
                return

            if optimizer is not None and hasattr(clf, "forward"):
                try:
                    preds = clf.forward(X_test_batch, return_logits=True)
                    loss = loss_fn(preds, y_test_batch.to(device))
                    optimizer.zero_grad(); loss.backward(); optimizer.step()
                except Exception:
                    pass

            elapsed = time.perf_counter() - start
            total_train_time += elapsed

    time_per_sample = total_train_time / max(1, train_n)
    print(f"Finetune pilot: total_time={total_train_time:.2f}s, train_rows={train_n}, time_per_sample={time_per_sample:.6f}s")


if __name__ == "__main__":
    main()
