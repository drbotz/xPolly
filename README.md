# xPolly

xPolly is a Python tool that helps you synthesize speech using Amazon Polly. It supports segment-based audio generation and allows manual pause placement via an intuitive GUI.

## Features

- 📄 Import text fragments from `.xlsx` or `.csv` files
- 🔊 Convert each fragment into audio using AWS Polly
- ⏸️ Manually select where pauses go via a second GUI
- 🧪 Limiting mode for debugging: restricts to a set number of rows
- 💡 Supports MP3, OGG, PCM formats

---

## Installation

### Requirements

- Python 3.8+
- AWS credentials set up (`boto3`)
- Dependencies:

```bash
pip install boto3 pandas tqdm pydub openpyxl
```

> You also need to install `ffmpeg` for `pydub` to work:
```bash
brew install ffmpeg      # macOS
sudo apt install ffmpeg  # Ubuntu/Debian
```

---

## Usage

### 1. Run the script

```bash
python xPolly.py
```

### 2. GUI: User Configuration

- Choose voice (Joanna, Matthew, etc.)
- Choose output format (mp3, ogg, pcm)
- Set pause duration (milliseconds)
- Browse for your input file
- Enable *Limiting Mode* and set max rows (optional)

### 3. GUI: Pause Placement

- Navigate pages (5 rows per page)
- Select "No Pause" or choose where to place a pause (e.g., between segment 2-3)
- Click *Generate Master Files* to produce combined audio

---

## File Format Example

Your Excel/CSV file should contain columns like:

```
Seg1 | Seg2 | Seg3 | Seg4 | Seg5 | ... | Column I
Text | Text | ...  | ...  | ...  |     | Full sentence
```

- Column I (9th column) is expected to contain the full sentence with the pause placeholder: `PAUSE`

---

## Output

- Each row generates a folder: `1/`, `2/`, ...
- Inside each folder:
  - Individual fragment files
  - `master.mp3` (final audio with pause)

---

## Git Usage

### Initial setup
```bash
git init
git add xPolly.py
git commit -m "Initial commit"
git remote add origin https://github.com/your-user/xPolly.git
git push -u origin main
```

---

## License
MIT License
