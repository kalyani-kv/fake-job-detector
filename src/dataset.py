"""Loading and preparing the job-postings dataset for the ML model."""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src.preprocessing import clean_text

TEXT_COLUMNS = ["title", "company_profile", "description", "requirements", "benefits"]
TARGET_COLUMN = "fraudulent"
TEST_SIZE = 0.2
RANDOM_STATE = 42


def load_dataset(csv_path):
    """Read the CSV and check that the columns we need exist."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at '{path}'. Download fake_job_postings.csv "
            "from Kaggle and place it in the data/ folder."
        )
    dataframe = pd.read_csv(path)
    missing = [c for c in TEXT_COLUMNS + [TARGET_COLUMN] if c not in dataframe.columns]
    if missing:
        raise ValueError(f"Dataset is missing expected columns: {missing}")
    return dataframe


def build_text(dataframe):
    """Join the text columns of each row into one cleaned string."""
    joined = dataframe[TEXT_COLUMNS].fillna("").astype(str).agg(" . ".join, axis=1)
    return joined.apply(clean_text)


def prepare_data(dataframe):
    """Return (data, duplicates_removed).

    `data` has two columns: 'text' and 'label' (1 = fraudulent).
    """
    dataframe = dataframe.dropna(subset=[TARGET_COLUMN])
    dataframe = dataframe[dataframe[TEXT_COLUMNS].notna().any(axis=1)]

    data = pd.DataFrame({
        "text": build_text(dataframe),
        "label": dataframe[TARGET_COLUMN].astype(int),
    })
    rows_before = len(data)
    data = data.drop_duplicates(subset="text").reset_index(drop=True)
    return data, rows_before - len(data)


def split_data(data):
    """Stratified train/test split, reproducible thanks to the fixed seed."""
    return train_test_split(
        data["text"],
        data["label"],
        test_size=TEST_SIZE,
        stratify=data["label"],
        random_state=RANDOM_STATE,
    )