#!/usr/bin/env python3
"""Analyze Excel file to understand finds structure"""

import pandas as pd
import sys
import os

def analyze_excel(file_path):
    """Analyze the Excel file structure"""
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        print(f"Excel file: {os.path.basename(file_path)}")
        print(f"Total rows: {len(df)}")
        print(f"Total columns: {len(df.columns)}")
        print("\n=== Column Names ===")
        for i, col in enumerate(df.columns, 1):
            print(f"{i}. {col}")
        
        print("\n=== Data Types ===")
        print(df.dtypes)
        
        print("\n=== First 5 rows ===")
        print(df.head())
        
        print("\n=== Sample Data ===")
        for col in df.columns:
            unique_count = df[col].nunique()
            null_count = df[col].isnull().sum()
            print(f"\n{col}:")
            print(f"  Unique values: {unique_count}")
            print(f"  Null values: {null_count}")
            if unique_count <= 10:
                print(f"  Values: {df[col].unique()[:10]}")
            else:
                print(f"  Sample values: {df[col].dropna().unique()[:5]}")
        
        # Check for find numbers
        if 'find_number' in df.columns or 'Find Number' in df.columns:
            col_name = 'find_number' if 'find_number' in df.columns else 'Find Number'
            print(f"\n=== Find Numbers ===")
            print(df[col_name].head(20))
        
        # Save to CSV for easier reading
        csv_path = file_path.replace('.xlsx', '_analyzed.csv')
        df.to_csv(csv_path, index=False)
        print(f"\n=== Saved to CSV: {csv_path} ===")
        
    except Exception as e:
        print(f"Error analyzing Excel: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    excel_path = "/Users/enzo/Downloads/LAGOI 2024 FINDS.xlsx"
    if os.path.exists(excel_path):
        analyze_excel(excel_path)
    else:
        print(f"File not found: {excel_path}")