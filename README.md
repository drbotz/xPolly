# xPolly

**xPolly** is a Python script that uses Amazon Polly to convert text from an Excel file into speech. It reads segments from each row of `stimuli.xlsx`, synthesizes them using Polly's "Joanna" voice, and saves each segment as an MP3 in its own folder.

## Features

- Reads text segments (`Seg1` to `Seg9`) from `stimuli.xlsx`
- Converts each text segment to speech using Amazon Polly
- Saves each MP3 in a separate folder for each row
- Progress tracking with `tqdm`

## Dependencies

Ensure the following Python packages are installed:

- `boto3`
- `pandas`
- `tqdm`
- `openpyxl` (for reading `.xlsx` files)

You can install them with:

```bash
pip install boto3 pandas tqdm openpyxl
