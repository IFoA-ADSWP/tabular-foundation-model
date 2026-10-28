import numpy as np


def frac_nonfinite(x):
    x = np.asarray(x, dtype=float)
    return float(np.mean(~np.isfinite(x)))


def mean_finite(x):
    x = np.asarray(x, dtype=float)
    finite = x[np.isfinite(x)]
    return float(np.mean(finite)) if finite.size else float("nan")


def rmse(y, yhat):
    y = np.asarray(y, dtype=float)
    yhat = np.asarray(yhat, dtype=float)
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def mae(y, yhat):
    y = np.asarray(y, dtype=float)
    yhat = np.asarray(yhat, dtype=float)
    return float(np.mean(np.abs(y - yhat)))


def empirical_p_zero(y):
    y = np.asarray(y)
    return float(np.mean(y == 0))


def summarize(model_name, arm, pi0, seed, y_test, mean_pred, native_nll, cont_nll, p_zero_pred, train_y_max):
    y_test = np.asarray(y_test, dtype=float)
    return {
        "model": model_name,
        "arm": arm,
        "pi0": pi0,
        "seed": seed,
        "n_test": len(y_test),
        "rmse": rmse(y_test, mean_pred),
        "mae": mae(y_test, mean_pred),
        "native_nll_mean": mean_finite(native_nll),
        "native_nll_frac_nonfinite": frac_nonfinite(native_nll),
        "cont_nll_mean": mean_finite(cont_nll),
        "cont_nll_frac_nonfinite": frac_nonfinite(cont_nll),
        "p_zero_pred_mean": float(np.mean(p_zero_pred)),
        "p_zero_empirical": empirical_p_zero(y_test),
        "train_y_max": float(train_y_max),
        "test_y_max": float(y_test.max()),
        "frac_test_y_exceeds_train_max": float(np.mean(y_test > train_y_max)),
    }
