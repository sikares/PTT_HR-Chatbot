import pandas as pd
import numpy as np
import re

def clean_excel_data(df):
    df_clean = df.copy()
    df_clean = df_clean.dropna(how='all')
    df_clean = df_clean.dropna(axis=1, how='all')
    
    for col in df_clean.columns:
        if df_clean[col].dtype == 'object':
            df_clean[col] = df_clean[col].astype(str)
            df_clean[col] = df_clean[col].str.strip()
            df_clean[col] = df_clean[col].replace(['nan', 'None', '', ' '], np.nan)
    
    return df_clean

def handle_merged_cells(df, key_columns):
    df_processed = df.copy()
    
    for col in key_columns:
        if col in df_processed.columns and col != "รายละเอียด Status":
            df_processed[col] = df_processed[col].fillna(method='ffill')
    
    return df_processed

def is_numbered_feedback(text):
    return bool(re.match(r"^\d+\.", str(text).strip()))

def group_related_rows(df, selected_columns):
    df_grouped = df.copy()
    
    group_id = 0
    prev_main_feedback = None
    group_ids = []

    for idx, row in df_grouped.iterrows():
        main_feedback = (
            row.get("ที่มาของ Feedback", "") or ""
        ) + "|" + (
            row.get("BU", "") or ""
        ) + "|" + (
            row.get("ประเภท Feedback", "") or ""
        )

        detail_text = str(row.get("รายละเอียด Feedback", "")).strip()
        has_numbered_start = is_numbered_feedback(detail_text)

        if idx == 0:
            group_id = 1
            prev_main_feedback = main_feedback
        else:
            if main_feedback != prev_main_feedback:
                group_id += 1
                prev_main_feedback = main_feedback
            elif not has_numbered_start and detail_text:
                group_id += 1
                prev_main_feedback = main_feedback

        group_ids.append(group_id)

    df_grouped["group_id"] = group_ids
    return df_grouped

def consolidate_groups(df_grouped, selected_columns):
    consolidated_data = []

    for group_id in df_grouped['group_id'].unique():
        group_data = df_grouped[df_grouped['group_id'] == group_id]
        consolidated_row = {}

        for col in selected_columns:
            if col == "รายละเอียด Status":
                status_values = group_data[col].dropna().unique()
                status_values = [str(val).strip() for val in status_values if str(val).strip() and str(val) != 'nan']
                consolidated_row[col] = ' | '.join(status_values) if status_values else "ไม่มีข้อมูล"
            elif col == "รายละเอียด Feedback":
                all_lines = group_data[col].dropna().astype(str).str.strip()
                full_feedback = "\n".join(all_lines)
                consolidated_row[col] = full_feedback
            else:
                non_null_values = group_data[col].dropna()
                if not non_null_values.empty:
                    consolidated_row[col] = str(non_null_values.iloc[0]).strip()
                else:
                    consolidated_row[col] = "ไม่มีข้อมูล"

        consolidated_data.append(consolidated_row)

    return pd.DataFrame(consolidated_data)

def clean_and_process_data(df, selected_columns):
    df_clean = clean_excel_data(df)

    missing_columns = [col for col in selected_columns if col not in df_clean.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    df_selected = df_clean[selected_columns].copy()
    
    df_merged = handle_merged_cells(df_selected, selected_columns)
    
    df_filtered = df_merged.dropna(how='all')
    
    df_grouped = group_related_rows(df_filtered, selected_columns)
    
    df_consolidated = consolidate_groups(df_grouped, selected_columns)
    
    df_final = df_consolidated.drop_duplicates()
    
    df_final = df_final.reset_index(drop=True)
    
    return df_final
