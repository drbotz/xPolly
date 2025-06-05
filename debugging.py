import tkinter as tk
from tkinter import filedialog
import pandas as pd

def choose_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select Excel file", filetypes=[("Excel files", "*.xlsx *.xls")])
    return file_path

def read_sentences_from_column_i(file_path):
    df = pd.read_excel(file_path)
    print("Available columns:", list(df.columns))
    col_index = 8  # 0-based index for column 9 (I)
    if col_index >= len(df.columns):
        raise ValueError("Column index 9 (I) is out of range in the spreadsheet.")

    sentences = df.iloc[:, col_index].dropna().tolist()
    for i, sentence in enumerate(sentences, start=2):
        print(f"I{i}: {sentence}")

if __name__ == '__main__':
    path = choose_file()
    if path:
        read_sentences_from_column_i(path)
    else:
        print("No file selected.")
