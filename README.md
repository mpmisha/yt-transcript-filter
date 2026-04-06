# yt-transcript-filter

Scrape YouTube channel/playlist transcripts and filter videos by topic.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### 1. Fetch transcripts from a channel or playlist

```bash
ytf fetch "https://www.youtube.com/playlist?list=PLxxxxxx" -o ./transcripts
ytf fetch "https://www.youtube.com/@ChannelName/videos" -o ./transcripts
```

### 2. Search transcripts by keyword

```bash
ytf search "machine learning" "neural network" -d ./transcripts
```

### 3. Filter videos by topic (include/exclude)

```bash
ytf filter -d ./transcripts --include "python" --include "tutorial" --exclude "sponsor"
```
