"""Print real facts about the dataset. Never quote numbers we did not measure."""

import pandas as pd

from src.dataset import TARGET_COLUMN, load_dataset, prepare_data

DATA_PATH = "data/fake_job_postings.csv"

pd.set_option("display.max_rows", 100)

dataframe = load_dataset(DATA_PATH)

print(f"Rows: {len(dataframe)}")
print(f"Columns ({len(dataframe.columns)}): {list(dataframe.columns)}")

print("\nMissing values per column:")
print(dataframe.isna().sum())

counts = dataframe[TARGET_COLUMN].value_counts()
print("\nTarget distribution (0 = real, 1 = fraudulent):")
print(counts)
print(f"Fraudulent share: {counts.get(1, 0) / len(dataframe):.1%}")

data, removed = prepare_data(dataframe)
print(f"\nDuplicate postings removed: {removed}")
print(f"Rows used for modelling: {len(data)}")