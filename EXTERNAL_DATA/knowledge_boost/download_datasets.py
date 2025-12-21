import os
import requests
import tqdm
from pathlib import Path

# Configuration
SAVE_DIR = Path("EXTERNAL_DATA")
DATASETS = {
    "ATOMIC_2020": "https://raw.githubusercontent.com/allenai/comet-atomic-2020/main/data/train.tsv",
    "FEVER_LITE": "https://s3-eu-west-1.amazonaws.com/fever.public/paper_dev.jsonl",
    "STACK_SMOL_PY": "https://huggingface.co/datasets/bigcode/the-stack-smol/resolve/main/data/python/train-00000-of-00001.parquet"
}

def download_file(url, filename, limit_bytes=None):
    print(f"📥 Downloading {filename} from {url}...")
    headers = {}
    if limit_bytes:
        headers['Range'] = f'bytes=0-{limit_bytes}'
    
    response = requests.get(url, headers=headers, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    path = SAVE_DIR / filename
    with open(path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"✅ Saved to {path}")

def main():
    SAVE_DIR.mkdir(exist_ok=True)
    
    # Custom Wikidata slice (First 10MB of latest dump)
    # Using a more stable mirror or direct access if range works
    wikidata_url = "https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.gz"
    download_file(wikidata_url, "wikidata_sample.json.gz", limit_bytes=10*1024*1024)
    
    for name, url in DATASETS.items():
        ext = url.split('.')[-1]
        download_file(url, f"{name.lower()}.{ext}")

if __name__ == "__main__":
    main()
