import os
import boto3
import pandas as pd
from tqdm import tqdm

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "stimuli.xlsx")
df = pd.read_excel(file_path)

polly = boto3.client("polly", region_name="us-east-1")

segment_columns = [f"Seg{i}" for i in range(1, 10)]

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
                    OutputFormat="mp3",
                    VoiceId="Joanna"
                )
                mp3_path = os.path.join(folder_path, f"{segment_number}.mp3")
                with open(mp3_path, "wb") as file:
                    file.write(response["AudioStream"].read())
                print(f"   💾 Saved to: {mp3_path}")
            except Exception as e:
                print(f"   ur trash ts didnt generate {segment_number}: {e}")
            segment_number += 1

print("\nLets go twin! We finished!")
