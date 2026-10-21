"""Train the TF-IDF + Logistic Regression model and save it."""

import argparse
import sys
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.dataset import load_dataset, prepare_data, split_data

DEFAULT_DATA_PATH = "data/fake_job_postings.csv"
MODEL_PATH = Path("models/model.pkl")


def build_pipeline():
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=2,
            max_features=50_000,
            stop_words="english",
            sublinear_tf=True,
        )),
        ("classifier", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
        )),
    ])


def show_top_terms(pipeline, count=15):
    """Print the words and phrases with the strongest influence."""
    terms = pipeline.named_steps["tfidf"].get_feature_names_out()
    weights = pipeline.named_steps["classifier"].coef_[0]
    order = weights.argsort()

    print("\nTerms pushing toward FRAUDULENT:")
    for index in order[-count:][::-1]:
        print(f"  {terms[index]:<30} {weights[index]:+.2f}")
    print("\nTerms pushing toward REAL:")
    for index in order[:count]:
        print(f"  {terms[index]:<30} {weights[index]:+.2f}")


def main():
    parser = argparse.ArgumentParser(description="Train the fake-job model.")
    parser.add_argument("--data", default=DEFAULT_DATA_PATH, help="Path to the CSV file")
    args = parser.parse_args()

    try:
        dataframe = load_dataset(args.data)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}")
        sys.exit(1)

    data, removed = prepare_data(dataframe)
    x_train, x_test, y_train, y_test = split_data(data)

    print(f"Duplicates removed: {removed}")
    print(f"Training rows: {len(x_train)} (fraudulent: {int(y_train.sum())})")
    print(f"Test rows:     {len(x_test)} (fraudulent: {int(y_test.sum())})")

    print("\nTraining model...")
    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

    show_top_terms(pipeline)


if __name__ == "__main__":
    main()