import streamlit as st
import pandas as pd
import os
import re
import io

def process_card_data(df, rows_to_delete_top=0, rows_to_delete_bottom=0):
    """Processes card data in a pandas DataFrame."""
    try:
        # 1) Remove top N rows
        df = df.iloc[rows_to_delete_top:].reset_index(drop=True)

        # 2) Find the row with 'Verified' within first 10 lines
        verified_header_index = None
        for i in range(min(10, len(df))):
            row_vals = df.iloc[i].astype(str).values
            if any("Verified" in cell for cell in row_vals):
                verified_header_index = i
                break

        if verified_header_index is None:
            raise ValueError("Could not find a row containing 'Verified' within the first 10 rows.")

        # 3) Set that row as the header
        df.columns = df.iloc[verified_header_index].values
        df = df.iloc[verified_header_index + 1:].reset_index(drop=True)

        # 4) Clean column names (convert NaN to "", strip spaces)
        cleaned_cols = []
        for col in df.columns:
            if pd.isnull(col):
                cleaned_cols.append("")
            else:
                cleaned_cols.append(str(col).strip())
        df.columns = cleaned_cols

        # 5) Rename all "" columns to CardHolderName1, CardHolderName2, etc.
        count_empty = 0
        for i, col in enumerate(df.columns):
            if col == "":
                count_empty += 1
                df.columns.values[i] = f"CardHolderName{count_empty}"

        # 6) Drop duplicate columns (keeping the first)
        df = df.loc[:, ~df.columns.duplicated()]

        # 7) Drop "Record#" if it exists
        if "Record#" in df.columns:
            df.drop(columns=["Record#"], inplace=True)

        # 8) Identify and rename CardHolderName column
        card_cols = [c for c in df.columns if c.startswith("CardHolderName")]
        chosen_col = None
        for c in card_cols:
             sample_values = df[c].dropna().astype(str).head(20)
             if any(re.search(r"\d+", val) for val in sample_values):
                 chosen_col = c
                 break
        if chosen_col is not None:
            df.rename(columns={chosen_col: "CardHolderName"}, inplace=True)
            for c in card_cols:
                if c != chosen_col:
                    df.drop(columns=[c], inplace=True, errors="ignore")

        # 9) Extract digits from "CardHolderName", forward-fill
        if "CardHolderName" in df.columns:
            df["Card No."] = df["CardHolderName"].astype(str).str.extract(r"(\d+)").ffill()
            df.drop(columns=["CardHolderName"], inplace=True)

        # 10) Keep only the final columns
        desired_cols = ["Card No.", "Verified", "Date", "Payee", "Charges"]
        existing_cols = [c for c in desired_cols if c in df.columns]
        df = df[existing_cols]

        # 11) Drop rows that are empty in Verified/Date/Payee/Charges
        check_cols = [c for c in existing_cols if c != "Card No."]
        df = df.dropna(subset=check_cols, how="all")

        # 12) Remove the last N rows
        if rows_to_delete_bottom > 0 and len(df) >= rows_to_delete_bottom:
            df = df.iloc[:-rows_to_delete_bottom]

        return df
    except Exception as e:
        st.error(f"Error during data processing: {e}")
        return None  # Return None in case of error

def download_csv(df):
    """Downloads a pandas DataFrame as a CSV file."""
    if df is not None:  # Check if DataFrame is valid
        csv_name = "cleaned_card_data.csv"
        csv_string = df.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="Download Cleaned CSV",
            data=csv_string,
            file_name=csv_name,
            mime="text/csv",
        )

st.set_page_config(page_title="Sage Data Cleaner", page_icon=":bar_chart:")

st.title("Sage Export Data Cleaner")

st.write(
    """
    This app helps you clean exported CSV data from Sage accounting software. 
    It performs several cleaning steps to prepare the data for analysis or import.

    **Instructions:**

    1.  **Upload your Sage export CSV file.**
    2.  **(Optional)** Adjust the number of rows to remove from the top and bottom of the file if needed. This is useful for removing headers or footers from the export.
    3.  Click the **Process Data** button.
    4.  Review the cleaned data preview.
    5.  Click the **Download Cleaned CSV** button to save the cleaned data.

    """
)

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    try:
        try:
            df = pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(uploaded_file, encoding='latin1')
            except UnicodeDecodeError:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
        except pd.errors.ParserError:
            st.error("Error: Could not parse the CSV file. Please check its format.")
            st.stop()
        
        num_rows_top = st.number_input("Rows to remove from top", min_value=0, value=0)
        num_rows_bottom = st.number_input("Rows to remove from bottom", min_value=0, value=0)

        if st.button("Process Data"):
            with st.spinner("Processing data..."):
                cleaned_df = process_card_data(df.copy(), num_rows_top, num_rows_bottom)
                if cleaned_df is not None: # Check if processing was successful
                    st.write("### Cleaned Data Preview:")
                    st.dataframe(cleaned_df)
                    download_csv(cleaned_df)
                

    except Exception as e:
        st.exception(e)
        st.error(f"An error occurred during file upload or processing: {e}")