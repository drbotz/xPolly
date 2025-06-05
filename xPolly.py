import os
import boto3
import pandas as pd
from tqdm import tqdm
from pydub import AudioSegment
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re

def get_user_config():
    config = {}

    def submit():
        config['voice'] = voice_var.get()
        config['format'] = format_var.get()
        config['file_path'] = file_path_var.get()
        config['pause_duration'] = int(pause_var.get())
        config['limit_rows'] = bool(limit_var.get())
        config['max_rows'] = int(max_rows_var.get()) if config['limit_rows'] else None
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
    root.geometry("420x400")

    ttk.Label(root, text="Select Voice:").pack(pady=5)
    voice_var = tk.StringVar(value="Joanna")
    voices = ["Joanna", "Matthew", "Ivy", "Justin", "Kendra"]
    ttk.Combobox(root, textvariable=voice_var, values=voices, state="readonly").pack()

    ttk.Label(root, text="Select Output Format:").pack(pady=5)
    format_var = tk.StringVar(value="mp3")
    formats = ["mp3", "ogg_vorbis", "pcm"]
    ttk.Combobox(root, textvariable=format_var, values=formats, state="readonly").pack()

    ttk.Label(root, text="Pause Duration (ms):").pack(pady=5)
    pause_var = tk.StringVar(value="500")
    ttk.Entry(root, textvariable=pause_var, width=10).pack()

    ttk.Label(root, text="Select Stimuli File:").pack(pady=5)
    file_path_var = tk.StringVar()
    ttk.Entry(root, textvariable=file_path_var, width=40).pack()
    ttk.Button(root, text="Browse", command=choose_file).pack(pady=5)

    limit_var = tk.IntVar()
    ttk.Checkbutton(root, text="Limiting Mode", variable=limit_var).pack(pady=5)

    ttk.Label(root, text="Max Rows (if limited):").pack(pady=5)
    max_rows_var = tk.StringVar(value="5")
    ttk.Entry(root, textvariable=max_rows_var, width=10).pack()

    ttk.Button(root, text="Start", command=submit).pack(pady=10)
    root.mainloop()

    return config

user_config = get_user_config()
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = user_config['file_path']

if file_path.endswith(".csv"):
    df = pd.read_csv(file_path)
else:
    df = pd.read_excel(file_path)

segment_columns = [col for col in df.columns if str(col).lower().startswith("seg")]
polly = boto3.client("polly", region_name="us-east-1")
print(f"Generating fragments for {len(df)} rows...\n")

audio_data = []

if user_config.get('limit_rows') and user_config.get('max_rows'):
    df = df.head(user_config['max_rows'])

for row_index, row in tqdm(df.iterrows(), total=len(df), desc="Generating", unit="row"):
    try:
        full_sentence = str(row.iloc[8]) if pd.notna(row.iloc[8]) else ""
        fragments = [str(row[col]).strip() for col in segment_columns if isinstance(row[col], str) and row[col].strip() and row[col].strip().upper() != "PAUSE"]

        folder_name = str(row_index + 1)
        folder_path = os.path.join(script_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        audio_fragments = []
        for i, frag in enumerate(fragments):
            response = polly.synthesize_speech(
                Text=frag,
                OutputFormat=user_config['format'],
                VoiceId=user_config['voice']
            )
            clean_text = re.sub(r'[\\/:*?"<>|]', '', frag.replace(' ', '_'))[:30]
            frag_filename = f"{i+1}_frag_{clean_text}.{user_config['format']}"
            frag_path = os.path.join(folder_path, frag_filename)
            with open(frag_path, "wb") as f:
                f.write(response["AudioStream"].read())
            audio_fragments.append((frag_path, frag))

        audio_data.append((row_index + 1, folder_path, audio_fragments))

    except Exception as e:
        print(f"   ⚠️ Error in row {row_index+1}: {e}")

# GUI for pause placement
selection = {}

def build_pause_selector():
    def save_and_build_audio():
        pause_ms = user_config['pause_duration']
        silence = AudioSegment.silent(duration=pause_ms)

        for idx, folder_path, fragments in audio_data:
            choice = pause_vars.get(idx).get()
            combined = AudioSegment.empty()

            for i, (frag_path, _) in enumerate(fragments):
                combined += AudioSegment.from_file(frag_path)
                if choice != "No Pause" and f"{i+1}-{i+2}" == choice:
                    combined += silence

            master_path = os.path.join(folder_path, f"master.{user_config['format']}")
            combined.export(master_path, format=user_config['format'])
            print(f"✅ Row {idx}: Saved {master_path}")

        pause_root.destroy()

    pause_root = tk.Tk()
    pause_root.title("Select Pause Placement")

    page_size = 5
    current_page = [0]  # use list for mutability in closure
    pause_vars = {}

    def draw_page():
        for widget in frame.winfo_children():
            widget.destroy()

        start = current_page[0] * page_size
        end = min(start + page_size, len(audio_data))

        for idx, _, fragments in audio_data[start:end]:
            frag_count = len(fragments)
            ttk.Label(frame, text=f"Sentence #{idx}").pack()
            var = tk.StringVar(value="No Pause")
            pause_vars[idx] = var

            pause_opts = ["No Pause"] + [f"{i+1}-{i+2}" for i in range(frag_count - 1)]
            ttk.Combobox(frame, textvariable=var, values=pause_opts, state="readonly").pack()

        nav_frame = ttk.Frame(frame)
        nav_frame.pack(pady=5)
        if current_page[0] > 0:
            ttk.Button(nav_frame, text="Previous Page", command=prev_page).pack(side="left", padx=5)
        if end < len(audio_data):
            ttk.Button(nav_frame, text="Next Page", command=next_page).pack(side="right", padx=5)

        ttk.Button(frame, text="Generate Master Files", command=save_and_build_audio).pack(pady=10)

    def next_page():
        current_page[0] += 1
        draw_page()

    def prev_page():
        current_page[0] -= 1
        draw_page()

    frame = ttk.Frame(pause_root)
    frame.pack(padx=10, pady=10)

    draw_page()
    pause_root.mainloop()

build_pause_selector()
print("\n✅ All done. Check folders for output audio.")
