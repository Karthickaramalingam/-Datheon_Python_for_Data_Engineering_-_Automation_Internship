
import pandas as pd
import logging
from pathlib import Path

# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).parent

INPUT_FILE = BASE_DIR / "messy_dataset.csv"
OUTPUT_FILE = BASE_DIR / "cleaned_dataset.csv"
REPORT_FILE = BASE_DIR / "validation_report.txt"

logging.basicConfig(
    filename=str(REPORT_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True
)

# --------------------------------------------------
# 2. DEFINE THE EXPECTED SCHEMA
# --------------------------------------------------

EXPECTED_COLUMNS = [
    "Customer_ID",
    "Customer_Name",
    "Amount",
    "Date",
    "City"
]

REQUIRED_COLUMNS = [
    "Customer_ID",
    "Customer_Name"
    
]

# --------------------------------------------------
# 3. CLEAN CURRENCY VALUES
# --------------------------------------------------

def clean_amount(value):
    """Convert currency strings into numeric values."""

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value.lower() in ["", "not available", "na", "n/a"]:
        return None

    # Remove currency symbols and thousands separators
    value = value.replace("₹", "")
    value = value.replace("$", "")
    value = value.replace(",", "")
    value = value.replace(" ", "")

    try:
        return float(value)
    except ValueError:
        return None


# --------------------------------------------------
# 4. CLEAN DATES
# --------------------------------------------------

def clean_date(value):
    """Convert supported date formats to YYYY-MM-DD."""

    if pd.isna(value):
        return pd.NaT

    value = str(value).strip()

    if value.lower() in ["", "invalid", "na", "n/a"]:
        return pd.NaT

    # The sample data uses day/month/year for slash dates.
    # ISO dates and dates containing month names are also supported.
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%b-%Y"
    ]

    for date_format in formats:
        try:
            return pd.to_datetime(
                value,
                format=date_format,
                errors="raise"
            )
        except (ValueError, TypeError):
            continue

    return pd.NaT


# --------------------------------------------------
# 5. MAIN DATA CLEANING PROCESS
# --------------------------------------------------

def clean_dataset():

    print("Starting automated data cleaning...")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    # Read every column as text first to preserve messy values.
    # on_bad_lines='error' prevents silently skipping malformed rows.
    df = pd.read_csv(
        INPUT_FILE,
        dtype=str,
        keep_default_na=False,
        on_bad_lines="error",
        index_col=False
    )

    initial_rows = len(df)

    logging.info("Data cleaning process started.")
    logging.info("Original row count: %s", initial_rows)

    # ----------------------------------------------
    # Validate schema
    # ----------------------------------------------

    missing_columns = [
        col for col in EXPECTED_COLUMNS
        if col not in df.columns
    ]

    unexpected_columns = [
        col for col in df.columns
        if col not in EXPECTED_COLUMNS
    ]

    if missing_columns:
        logging.error("Missing columns: %s", missing_columns)
        raise ValueError(
            f"Schema validation failed. Missing columns: {missing_columns}"
        )

    if unexpected_columns:
        logging.warning(
            "Unexpected columns: %s", unexpected_columns
        )

    # Keep columns in the expected order.
    df = df[EXPECTED_COLUMNS].copy()

    # ----------------------------------------------
    # Normalize empty strings and whitespace
    # ----------------------------------------------

    for column in df.columns:
        df[column] = df[column].astype("string").str.strip()
        df[column] = df[column].replace("", pd.NA)

    # ----------------------------------------------
    # Convert data types
    # ----------------------------------------------

    df["Customer_ID"] = pd.to_numeric(
        df["Customer_ID"],
        errors="coerce"
    ).astype("Int64")

    df["Amount"] = df["Amount"].apply(clean_amount)

    df["Date"] = df["Date"].apply(clean_date)

    # Normalize text columns
    df["Customer_Name"] = (
        df["Customer_Name"].str.strip().str.title()
    )

    df["City"] = df["City"].str.strip().str.title()

    # ----------------------------------------------
    # Remove duplicate records
    # ----------------------------------------------

    duplicates_removed = int(df.duplicated().sum())

    df = df.drop_duplicates().copy()

    # ----------------------------------------------
    # Log invalid and missing values
    # ----------------------------------------------

    missing_before_handling = df.isna().sum().to_dict()

    logging.info(
        "Missing values after normalization: %s",
        missing_before_handling
    )

    # Drop rows missing essential information.
    # Amount and Date are retained as missing so the data
    # quality issues remain visible in the output.
    before_required_filter = len(df)

    df = df.dropna(subset=REQUIRED_COLUMNS).copy()

    rows_removed_missing_required = (
        before_required_filter - len(df)
    )

    # Fill optional missing city values.
    df["City"] = df["City"].fillna("Unknown")

    # Use explicit nullable types.
    df["Customer_ID"] = df["Customer_ID"].astype("Int64")
    df["Amount"] = df["Amount"].astype("Float64")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # ----------------------------------------------
    # Final validation
    # ----------------------------------------------

    schema_valid = list(df.columns) == EXPECTED_COLUMNS

    final_missing_values = df.isna().sum().to_dict()

    logging.info("Final schema valid: %s", schema_valid)
    logging.info("Final missing values: %s", final_missing_values)
    logging.info("Duplicate rows removed: %s", duplicates_removed)
    logging.info(
        "Rows removed for missing required fields: %s",
        rows_removed_missing_required
    )

    # Save normalized dates and amounts.
    df.to_csv(
        OUTPUT_FILE,
        index=False,
        date_format="%Y-%m-%d"
    )

    # ----------------------------------------------
    # Generate validation report
    # ----------------------------------------------

    report_lines = [
        "AUTOMATED DATA CLEANING REPORT",
        "=" * 40,
        f"Original rows: {initial_rows}",
        f"Final rows: {len(df)}",
        f"Duplicate rows removed: {duplicates_removed}",
        (
            "Rows removed for missing required fields: "
            f"{rows_removed_missing_required}"
        ),
        f"Schema validation passed: {schema_valid}",
        "",
        "Final column data types:",
        df.dtypes.to_string(),
        "",
        "Missing values in final dataset:",
        str(final_missing_values),
        "",
        f"Cleaned dataset saved to: {OUTPUT_FILE.name}",
        "Note: Missing or invalid Amount and Date values are retained as empty fields."
    ]

    report = "\n".join(report_lines)

    with open(REPORT_FILE, "a", encoding="utf-8") as file:
        file.write("\n\n" + report + "\n")

    print("\nData cleaning completed successfully!")
    print(report)
    print("\nOutput files created:")
    print(OUTPUT_FILE)
    print(REPORT_FILE)


# --------------------------------------------------
# 6. RUN THE PROGRAM
# --------------------------------------------------

if __name__ == "__main__":
    try:
        clean_dataset()
    except Exception as error:
        logging.exception("Data cleaning failed.")
        print(f"ERROR: {error}")
