# xPolly 6/9/2025 - Summer Lab
# v9.4 - tight silence trimming using split_to_mono, .strip_silence()

import os
import sys
import boto3
import pandas as pd
from tqdm import tqdm
from pydub import AudioSegment, silence
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import shutil
import io


def strip_silence(audio, silence_thresh=-50, padding=5):
    """
    Trims leading and trailing silence very aggressively and optionally adds back a small padding (ms).
    """
    non_silent = silence.detect_nonsilent(audio, min_silence_len=40, silence_thresh=silence_thresh)
    if not non_silent:
        return audio
    start = max(0, non_silent[0][0] - padding)
    end = min(len(audio), non_silent[-1][1] + padding)
    return audio[start:end]


def get_user_config():
    config = {}
    cancelled = {'value': False}

    def submit():
        if not file_path_var.get():
            messagebox.showerror("Input Required", "pls select a file")
            return
        config['voice'] = voice_var.get()
        config['format'] = format_var.get()
        config['file_path'] = file_path_var.get()
        config['pause_duration'] = int(pause_var.get())
        config['limit_rows'] = bool(limit_var.get())
        config['max_rows'] = int(max_rows_var.get()) if config['limit_rows'] else None
        config['fragment_only'] = bool(fragment_only_var.get())
        config['sentences_per_page'] = int(sentences_per_page_var.get())
        config['sheet'] = sheet_var.get() if file_path_var.get().endswith('.xlsx') else None
        config['trim_silence'] = bool(trim_silence_var.get())
        root.quit()
        root.destroy()

    def cancel():
        cancelled['value'] = True
        root.quit()
        root.destroy()

    def choose_file():
        filename = filedialog.askopenfilename(filetypes=[["Excel or CSV files", "*.xlsx *.csv"]])
        file_path_var.set(filename)
        if filename.endswith('.xlsx'):
            try:
                xl = pd.ExcelFile(filename)
                sheet_var.set(xl.sheet_names[0])
                sheet_dropdown['values'] = xl.sheet_names
                sheet_dropdown.set(xl.sheet_names[0])
                sheet_dropdown.pack()
            except Exception as e:
                messagebox.showerror("Error", f"Excel read fail: {e}")

    root = tk.Tk()
    root.title("Polly Voice Synthesizer")
    root.geometry("450x650")

    voice_var = tk.StringVar(value="Matthew")
    format_var = tk.StringVar(value="mp3")
    pause_var = tk.StringVar(value="500")
    file_path_var = tk.StringVar()
    limit_var = tk.IntVar()
    max_rows_var = tk.StringVar(value="5")
    fragment_only_var = tk.IntVar()
    sentences_per_page_var = tk.StringVar(value="10")
    sheet_var = tk.StringVar()
    trim_silence_var = tk.IntVar(value=1)

    ttk.Label(root, text="Select Voice:").pack(pady=5)
    ttk.Combobox(root, textvariable=voice_var, values=["Joanna", "Matthew", "Ivy", "Justin", "Kendra"], state="readonly").pack()

    ttk.Label(root, text="Select Output Format:").pack(pady=5)
    ttk.Combobox(root, textvariable=format_var, values=["mp3", "ogg_vorbis", "pcm"], state="readonly").pack()

    ttk.Label(root, text="Pause Duration (ms):").pack(pady=5)
    ttk.Entry(root, textvariable=pause_var, width=10).pack()

    ttk.Label(root, text="Select Stimuli File:").pack(pady=5)
    ttk.Entry(root, textvariable=file_path_var, width=40).pack()
    ttk.Button(root, text="Browse", command=choose_file).pack(pady=5)

    ttk.Label(root, text="Select Sheet (if Excel):").pack()
    sheet_dropdown = ttk.Combobox(root, textvariable=sheet_var, state="readonly")
    sheet_dropdown.pack()

    ttk.Checkbutton(root, text="Limiting Mode", variable=limit_var).pack(pady=5)
    ttk.Label(root, text="Max Rows (if limited):").pack(pady=5)
    ttk.Entry(root, textvariable=max_rows_var, width=10).pack()

    ttk.Checkbutton(root, text="Fragment Only Mode", variable=fragment_only_var).pack(pady=5)
    ttk.Label(root, text="Sentences per Page (Pause Editor):").pack(pady=5)
    ttk.Entry(root, textvariable=sentences_per_page_var, width=10).pack()

    ttk.Checkbutton(root, text="Trim Silence in Fragments", variable=trim_silence_var).pack(pady=10)

    frame = ttk.Frame(root)
    frame.pack(pady=10)
    ttk.Button(frame, text="Start", command=submit).pack(side="left", padx=10)
    ttk.Button(frame, text="Cancel", command=cancel).pack(side="right", padx=10)

    root.mainloop()

    if cancelled['value']:
        sys.exit("canceled by op")

    return config


user_config = get_user_config()
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = user_config['file_path']

if file_path.endswith(".csv"):
    df = pd.read_csv(file_path)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    folder_prefix = base_name
elif file_path.endswith(".xlsx"):
    if user_config.get("sheet"):
        df = pd.read_excel(file_path, sheet_name=user_config["sheet"])
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        folder_prefix = f"{user_config['sheet']}-{base_name}"
    else:
        df = pd.read_excel(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        folder_prefix = base_name
else:
    sys.exit("U cant use that file")

output_root = os.path.join(script_dir, folder_prefix)
os.makedirs(output_root, exist_ok=True)

segment_columns = [col for col in df.columns if str(col).lower().startswith("seg")]
polly = boto3.client("polly", region_name="us-east-1")

print(f"Generating fragments for {len(df)} rows...\n")

audio_data = []

if user_config.get('limit_rows') and user_config.get('max_rows'):
    df = df.head(user_config['max_rows'])

for row_index, row in tqdm(df.iterrows(), total=len(df), desc="Generating", unit="row"):
    try:
        folder_name = str(row_index + 1)
        folder_path = os.path.join(output_root, folder_name)
        segments = [str(row[col]).strip() for col in segment_columns if isinstance(row[col], str) and row[col].strip() and row[col].strip().upper() != "PAUSE"]
        os.makedirs(folder_path, exist_ok=True)
        fragments = []

        for i, frag in enumerate(segments):
            response = polly.synthesize_speech(Text=frag, OutputFormat=user_config['format'], VoiceId=user_config['voice'])
            clean_text = re.sub(r'[\\/:*?"<>|]', '', frag.replace(' ', '_'))[:30]
            frag_filename = f"{i+1}_frag_{clean_text}.{user_config['format']}"
            frag_path = os.path.join(folder_path, frag_filename)

            raw_audio = AudioSegment.from_file(io.BytesIO(response["AudioStream"].read()), format=user_config['format'])
            if user_config['trim_silence']:
                raw_audio = strip_silence(raw_audio, silence_thresh=-48, padding=0)

            raw_audio.export(frag_path, format=user_config['format'])
            fragments.append((frag_path, frag))

        audio_data.append((row_index + 1, folder_path, fragments, df.index[row_index]))

    except Exception as e:
        print(f"row {row_index+1} error: {e}")

print("\nfrag gen done.")

if not user_config.get("fragment_only"):
    def build_pause_selector():
        pause_ms = user_config['pause_duration']
        per_page = user_config.get('sentences_per_page', 10)
        total = len(audio_data)
        pages = (total + per_page - 1) // per_page
        current_page = {'index': 0}

        pause_root = tk.Tk()
        pause_root.title("Pause Selector")
        container = ttk.Frame(pause_root)
        container.pack(padx=10, pady=10)

        pause_vars = {}

        def render_page():
            for widget in container.winfo_children():
                widget.destroy()

            start = current_page['index'] * per_page
            end = min(start + per_page, total)
            for display_idx, _, fragments, excel_row in audio_data[start:end]:
                label = f"Sentence #{display_idx} (Row {excel_row + 2})"
                ttk.Label(container, text=label).pack()
                opts = ["No Pause"] + [f"{fragments[i][1]} -> {fragments[i+1][1]}" for i in range(len(fragments)-1)]
                var = pause_vars.setdefault(display_idx, tk.StringVar(value="No Pause"))
                ttk.Combobox(container, textvariable=var, values=opts, state="readonly").pack()

            nav_frame = ttk.Frame(container)
            nav_frame.pack(pady=10)
            if current_page['index'] > 0:
                ttk.Button(nav_frame, text="Previous", command=lambda: change_page(-1)).pack(side="left", padx=5)
            if current_page['index'] < pages - 1:
                ttk.Button(nav_frame, text="Next", command=lambda: change_page(1)).pack(side="left", padx=5)
            ttk.Button(nav_frame, text="Generate Master Files", command=save_and_build_audio).pack(side="left", padx=5)

        def change_page(direction):
            current_page['index'] += direction
            render_page()

        def save_and_build_audio():
            silence_seg = AudioSegment.silent(duration=pause_ms)
            central_master_folder = os.path.join(output_root, "AllMasters")
            os.makedirs(central_master_folder, exist_ok=True)

            for idx, folder_path, fragments, row_idx in audio_data:
                choice = pause_vars.get(idx, tk.StringVar(value="No Pause")).get()
                combined = AudioSegment.empty()
                for i, (frag_path, _) in enumerate(fragments):
                    combined += AudioSegment.from_file(frag_path)
                    if choice != "No Pause" and i + 1 < len(fragments):
                        if choice == f"{fragments[i][1]} -> {fragments[i+1][1]}":
                            combined += silence_seg

                try:
                    row_id_value = str(df.iloc[row_idx, 7]).strip()
                    if not row_id_value:
                        raise ValueError("Missing ID in column H")
                except Exception as e:
                    print(f"Row {row_idx + 2}: invalid ID in column H - {e}")
                    row_id_value = f"row_{row_idx+2}"

                master_filename = f"{row_id_value}.{user_config['format']}"
                master_path = os.path.join(folder_path, master_filename)
                combined.export(master_path, format=user_config['format'])
                print(f"Row {idx}: saved {master_path}")
                shutil.copy(master_path, os.path.join(central_master_folder, master_filename))

            pause_root.quit()
            pause_root.destroy()

        render_page()
        pause_root.mainloop()

    build_pause_selector()

print("\n DONE. go check the output folders.")
