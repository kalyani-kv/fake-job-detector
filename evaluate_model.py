"""Evaluate the saved model on the held-out test set."""

import json
import sys
from pathlib import Path

import joblib
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.dataset import load_dataset, prepare_data, split_data

DATA_PATH = "data/fake_job_postings.csv"
MODEL_PATH = Path("models/model.pkl")
METRICS_PATH = Path("models/metrics.json")
DECISION_THRESHOLD = 0.5
THRESHOLDS_TO_TRY = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


def load_model(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Model not found at '{path}'. Run train_model.py first."
        )
    return joblib.load(path)


def print_threshold_table(y_true, probabilities):
    print("\nPrecision / recall at different thresholds (fraudulent class):")
    print(f"  {'threshold':<10}{'precision':<11}{'recall':<9}{'flagged'}")
    for threshold in THRESHOLDS_TO_TRY:
        predicted = (probabilities >= threshold).astype(int)
        precision = precision_score(y_true, predicted, zero_division=0)
        recall = recall_score(y_true, predicted, zero_division=0)
        print(f"  {threshold:<10}{precision:<11.3f}{recall:<9.3f}{int(predicted.sum())}")


def main():
    try:
        dataframe = load_dataset(DATA_PATH)
        model = load_model(MODEL_PATH)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}")
        sys.exit(1)

    data, _ = prepare_data(dataframe)
    _, x_test, _, y_test = split_data(data)

    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= DECISION_THRESHOLD).astype(int)

    baseline_accuracy = 1 - y_test.mean()
    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions, zero_division=0)
    recall = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)
    pr_auc = average_precision_score(y_test, probabilities)
    roc_auc = roc_auc_score(y_test, probabilities)
    true_neg, false_pos, false_neg, true_pos = confusion_matrix(y_test, predictions).ravel()

    print(f"Test postings: {len(y_test)} (fraudulent: {int(y_test.sum())})")
    print(f"\nBaseline accuracy (always predict 'real'): {baseline_accuracy:.3f}")
    print(f"Model accuracy:  {accuracy:.3f}")
    print(f"Precision:       {precision:.3f}")
    print(f"Recall:          {recall:.3f}")
    print(f"F1-score:        {f1:.3f}")
    print(f"PR-AUC:          {pr_auc:.3f}")
    print(f"ROC-AUC:         {roc_auc:.3f}")

    print("\nConfusion matrix (threshold 0.5):")
    print("                    predicted real   predicted fake")
    print(f"  actually real     {true_neg:<17}{false_pos}")
    print(f"  actually fake     {false_neg:<17}{true_pos}")
    print(f"\n  False positives (real job flagged as fake): {false_pos}")
    print(f"  False negatives (scam missed):              {false_neg}")

    print("\nFull report:")
    print(classification_report(
        y_test, predictions, target_names=["real", "fraudulent"], zero_division=0))

    print_threshold_table(y_test, probabilities)

    metrics = {
        "test_rows": int(len(y_test)),
        "test_fraudulent": int(y_test.sum()),
        "baseline_accuracy": round(float(baseline_accuracy), 4),
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "pr_auc": round(float(pr_auc), 4),
        "roc_auc": round(float(roc_auc), 4),
        "true_negatives": int(true_neg),
        "false_positives": int(false_pos),
        "false_negatives": int(false_neg),
        "true_positives": int(true_pos),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nMetrics saved to {METRICS_PATH}")


if __name__ == "__main__":
    main()