import os
import pandas as pd
import numpy as np
from feature_extractor import get_features  # Importing the feature extraction module (feature_extractor.py)
import argparse
from warnings import warn
import sys
import datetime

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--input_directory_path', type=str, default=None, help='path to the directory where the input CSV files are stored')
    parser.add_argument('--output_directory_path', type=str, default=None, help='path to the directory where the output ECG feature CSV file will be saved')
    parser.add_argument('--sample_frequency', type=int, default=500, help='sampling frequency of the ECG data')
    args, unk = parser.parse_known_args()
    if unk:
        warn("Unknown arguments:" + str(unk) + ".")   
    
    # Path and initial setup
    input_directory = args.input_directory_path
    output_directory = args.output_directory_path
    os.makedirs(output_directory, exist_ok=True)
    output_csv = os.path.join(output_directory, "ecg_features.csv")
        
    # Set standard error output to avoid printing warnings
    # Add date and time to the standard error output file name
    stderr_filename = 'stderr_' + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + '.txt'
    f = open(os.path.join(args.output_directory_path, stderr_filename), 'w')
    sys.stderr = f

    # Initialize DataFrame for results
    result_df = pd.DataFrame()
    sample_frequency = args.sample_frequency

    # Feature extraction from each CSV
    feature_extractor = get_features()
    for filename in os.listdir(input_directory):
        if filename.endswith(".csv"):
            csv_file_path = os.path.join(input_directory, filename)
            df = pd.read_csv(csv_file_path, index_col=False, encoding="cp932")
            # check if there are any NaN values or string values in the dataframe
            if df.isnull().values.any() or df.select_dtypes(include=['object']).values.any():
                raise ValueError(f"Invalid data in {filename}. Please check the data and try again.")
            # Pass each lead column to the feature extractor and 
            for lead_column in df.columns:
                lead_data = df[lead_column].values
                features_lead, feature_names_lead, peak_indices_lead = feature_extractor.featurize_ecg(lead_data, sample_frequency)
                result_row = pd.DataFrame([features_lead], columns=feature_names_lead)
                result_row.insert(0, "ecg_id", filename.replace(".csv", "")) # Remove the file extension
                result_row.insert(1, "Lead_Column", lead_column)
                result_row.insert(2, "Column_Number", df.columns.get_loc(lead_column) + 1)
                result_df = pd.concat([result_df, result_row], ignore_index=True)

    # Group duplicates in memory
    duplicates_grouped = result_df.groupby('ecg_id').apply(lambda x: x.reset_index(drop=True)).unstack().reset_index()
    duplicates_grouped.columns = [f'{col[0]}_{col[1]}' if col[1] != '' else col[0] for col in duplicates_grouped.columns]

    # Replace column names based on predefined dictionary
    replacement_dict = {
        "_10": "_V5",
        "_11": "_V6",
        "_0": "_I",
        "_1": "_II",
        "_2": "_III",
        "_3": "_aVR",
        "_4": "_aVL",
        "_5": "_aVF",
        "_6": "_V1",
        "_7": "_V2",
        "_8": "_V3",
        "_9": "_V4"
    }

    def replace_column_names(columns, replacement_dict):
        new_columns = []
        for col in columns:
            for old_str, new_str in replacement_dict.items():
                col = col.replace(old_str, new_str)
            new_columns.append(col)
        return new_columns

    duplicates_grouped.columns = replace_column_names(duplicates_grouped.columns, replacement_dict)

    # Delete columns 2-37
    columns_to_drop = duplicates_grouped.columns[1:37]
    duplicates_grouped = duplicates_grouped.drop(columns=columns_to_drop)

    # Save the final DataFrame
    duplicates_grouped.to_csv(output_csv, index=False)

    print("Process completed. Final results saved to:", output_csv)
    
    # Close standard error output
    f.close()
    sys.stderr = sys.__stderr__