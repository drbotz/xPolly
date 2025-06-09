import os
import sys
import boto3
import pandas as pd
from tqdm import tqdm
from pydub import AudioSegment
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re

def get_user_config():
    config = {}
    cancelled = {'value': False}

    def submit():
        if not file_path_var.get():
            messagebox.showerror("Input Required", "Please select a data file.")
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
        root.destroy()

    def cancel():
        cancelled['value'] = True
        root.destroy()

    def choose_file():
        filename = filedialog.askopenfilename(filetypes=[("Excel or CSV files", "*.xlsx *.csv")])
        file_path_var.set(filename)
        if filename.endswith('.xlsx'):
            try:
                xl = pd.ExcelFile(filename)
                sheet_var.set(xl.sheet_names[0])
                sheet_dropdown['values'] = xl.sheet_names
                sheet_dropdown.set(xl.sheet_names[0])
                sheet_dropdown.pack()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read Excel file: {e}")

    root = tk.Tk()
    root.title("Polly Voice Synthesizer")
    root.geometry("450x600")

    voice_var = tk.StringVar(value="Joanna")
    format_var = tk.StringVar(value="mp3")
    pause_var = tk.StringVar(value="500")
    file_path_var = tk.StringVar()
    limit_var = tk.IntVar()
    max_rows_var = tk.StringVar(value="5")
    fragment_only_var = tk.IntVar()
    sentences_per_page_var = tk.StringVar(value="10")
    sheet_var = tk.StringVar()
    
    ttk.Label(root, text="Select Voice:").pack(pady=5)
    ttk.Combobox(root, textvariable=voice_var, values=["Joanna", "Matthew", "Ivy", "Justin", "Kendra"], state="readonly").pack()

    ttk.Label(root, text="Select Output Format:").pack(pady=5)
    ttk.Combobox(root, textvariable=format_var, values=["mp3", "ogg_vorbis", "pcm"], state="readonly").pack()

    ttk.Label(root, text="Pause Duration (ms):").pack(pady=5)
    ttk.Entry(root, textvariable=pause_var, width=10).pack()

    ttk.Label(root, text="Select Stimuli File:").pack(pady=5)
    entry = ttk.Entry(root, textvariable=file_path_var, width=40)
    entry.pack()
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

    frame = ttk.Frame(root)
    frame.pack(pady=10)
    ttk.Button(frame, text="Start", command=submit).pack(side="left", padx=10)
    ttk.Button(frame, text="Cancel", command=cancel).pack(side="right", padx=10)

    root.mainloop()

    if cancelled['value']:
        sys.exit("❌ Operation cancelled by user.")

    return config

# Load file
user_config = get_user_config()
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = user_config['file_path']

if file_path.endswith(".csv"):
    df = pd.read_csv(file_path)
elif file_path.endswith(".xlsx"):
    if user_config.get("sheet"):
        df = pd.read_excel(file_path, sheet_name=user_config["sheet"])
    else:
        df = pd.read_excel(file_path)
else:
    sys.exit("❌ Unsupported file type.")

segment_columns = [col for col in df.columns if str(col).lower().startswith("seg")]
polly = boto3.client("polly", region_name="us-east-1")

print(f"Generating fragments for {len(df)} rows...\n")
audio_data = []

if user_config.get('limit_rows') and user_config.get('max_rows'):
    df = df.head(user_config['max_rows'])

for row_index, row in tqdm(df.iterrows(), total=len(df), desc="Generating", unit="row"):
    try:
        folder_name = str(row_index + 1)
        folder_path = os.path.join(script_dir, folder_name)

        if os.path.exists(folder_path) and any(fname.endswith(f".{user_config['format']}") for fname in os.listdir(folder_path)):
            fragments = []
            for fname in sorted(os.listdir(folder_path)):
                if fname.startswith("_") or not fname.endswith(user_config['format']):
                    continue
                frag_path = os.path.join(folder_path, fname)
                fragments.append((frag_path, os.path.splitext(fname)[0]))
            if fragments:
                audio_data.append((row_index + 1, folder_path, fragments))
                continue

        segments = [str(row[col]).strip() for col in segment_columns if isinstance(row[col], str) and row[col].strip() and row[col].strip().upper() != "PAUSE"]

        os.makedirs(folder_path, exist_ok=True)
        fragments = []
        for i, frag in enumerate(segments):
            response = polly.synthesize_speech(Text=frag, OutputFormat=user_config['format'], VoiceId=user_config['voice'])
            clean_text = re.sub(r'[\\/:*?"<>|]', '', frag.replace(' ', '_'))[:30]
            frag_filename = f"{i+1}_frag_{clean_text}.{user_config['format']}"
            frag_path = os.path.join(folder_path, frag_filename)
            with open(frag_path, "wb") as f:
                f.write(response["AudioStream"].read())
            fragments.append((frag_path, frag))

        audio_data.append((row_index + 1, folder_path, fragments))

    except Exception as e:
        print(f"   ⚠️ Error in row {row_index+1}: {e}")

print("\nFragment generation complete.")

if not user_config.get("fragment_only"):
    def build_pause_selector():
        pause_ms = user_config['pause_duration']
        per_page = user_config.get('sentences_per_page', 10)
        total = len(audio_data)
        pages = (total + per_page - 1) // per_page
        current_page = {'index': 0}

        pause_root = tk.Tk()
        pause_root.title("Select Pause Placement")
        container = ttk.Frame(pause_root)
        container.pack(padx=10, pady=10)

        pause_vars = {}

        def render_page():
            for widget in container.winfo_children():
                widget.destroy()

            start = current_page['index'] * per_page
            end = min(start + per_page, total)
            for idx, _, fragments in audio_data[start:end]:
                ttk.Label(container, text=f"Sentence #{idx}").pack()
                opts = ["No Pause"] + [f"{fragments[i][1]} -> {fragments[i+1][1]}" for i in range(len(fragments)-1)]
                var = pause_vars.setdefault(idx, tk.StringVar(value="No Pause"))
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
            silence = AudioSegment.silent(duration=pause_ms)
            for idx, folder_path, fragments in audio_data:
                choice = pause_vars.get(idx, tk.StringVar(value="No Pause")).get()
                combined = AudioSegment.empty()
                for i, (frag_path, _) in enumerate(fragments):
                    combined += AudioSegment.from_file(frag_path)
                    if choice != "No Pause" and i + 1 < len(fragments):
                        if choice == f"{fragments[i][1]} -> {fragments[i+1][1]}":
                            combined += silence
                master_path = os.path.join(folder_path, f"master.{user_config['format']}")
                combined.export(master_path, format=user_config['format'])
                print(f"✅ Row {idx}: Saved {master_path}")
            pause_root.destroy()

        render_page()
        pause_root.mainloop()

    build_pause_selector()

print("\n✅ All done. Check folders for output audio.")
tk.mainloop()
