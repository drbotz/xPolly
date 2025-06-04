import os
import boto3
import pandas as pd
from tqdm import tqdm
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# GUI Setup

def get_user_config():
    config = {}

    def submit():
        config['voice'] = voice_var.get()
        config['format'] = format_var.get()
        config['file_path'] = file_path_var.get()
        if not config['file_path']:
            messagebox.showerror("Input Required", "Please select a data file.")
            return
        root.destroy()

    def choose_file():
        filename = filedialog.askopenfilename(
            filetypes=[("Excel or CSV files", "*.xlsx *.csv")]
        )
        file_path_var.set(filename)

    root = tk.Tk()
    root.title("Polly Voice Synthesizer")
    root.geometry("420x250")

    ttk.Label(root, text="Select Voice:").pack(pady=5)
    voice_var = tk.StringVar(value="Joanna")
    voices = ["Joanna", "Matthew", "Ivy", "Justin", "Kendra"]
    ttk.Combobox(root, textvariable=voice_var, values=voices, state="readonly").pack()

    ttk.Label(root, text="Select Output Format:").pack(pady=5)
    format_var = tk.StringVar(value="mp3")
    formats = ["mp3", "ogg_vorbis", "pcm"]
    ttk.Combobox(root, textvariable=format_var, values=formats, state="readonly").pack()

    ttk.Label(root, text="Select Stimuli File:").pack(pady=5)
    file_path_var = tk.StringVar()
    ttk.Entry(root, textvariable=file_path_var, width=40).pack()
    ttk.Button(root, text="Browse", command=choose_file).pack(pady=5)

    ttk.Button(root, text="Start", command=submit).pack(pady=10)
    root.mainloop()

    return config

# Get user selections
user_config = get_user_config()

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = user_config['file_path']

# Load file based on extension
if file_path.endswith(".csv"):
    df = pd.read_csv(file_path)
    segment_columns = [col for col in df.columns if col.lower().startswith("seg")]
else:
    df = pd.read_excel(file_path)
    segment_columns = [f"Seg{i}" for i in range(1, 10)]  # Default format

polly = boto3.client("polly", region_name="us-east-1")
print(f"Processing {len(df)} ts...\n")

for row_index, row in tqdm(df.iterrows(), total=len(df), desc="Rows", unit="row"):
    folder_name = str(row_index + 1)
    folder_path = os.path.join(script_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    print(f"\nProcessing ts {folder_name}")
    print(f"   I made a folder  at: {folder_path}")

    segment_number = 1
    for col in segment_columns:
        text = row.get(col)
        if isinstance(text, str) and text.strip():
            print(f"   🔊 Segment {segment_number}: \"{text}\"")
            try:
                response = polly.synthesize_speech(
                    Text=text,
                    OutputFormat=user_config['format'],
                    VoiceId=user_config['voice']
                )
                mp3_path = os.path.join(folder_path, f"{segment_number}.{user_config['format']}")
                with open(mp3_path, "wb") as file:
                    file.write(response["AudioStream"].read())
                print(f"   💾 Saved to: {mp3_path}")
            except Exception as e:
                print(f"   ur trash ts didnt generate {segment_number}: {e}")
            segment_number += 1

print("\nLets go twin! We finished!")
