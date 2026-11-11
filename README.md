# trendbrief-ai

Command-line tools for turning **what people are searching for right now** into short explainer videos.

* `fetch_trends.py` pulls the top Google Search trends for a region (Google Trends; no API key needed).
* `fetch_youtube_trends.py` pulls YouTube's most-popular videos for a region (YouTube Data API v3).
* `generate_video.py` turns a URL, file or pasted text into a narrated video overview with NotebookLM and downloads the MP4.

**Status: early prototype.** The pieces above work individually. The planned next stage chains them into one pipeline: source verification, a multi-agent script, automated quality checks and scheduled publishing.

## Video generation (NotebookLM)

Small Python CLI that uses [notebooklm-py](https://github.com/teng-lin/notebooklm-py) to create a notebook from a source, generate a Video Overview, and download the MP4.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
notebooklm login
notebooklm auth check --test
```

`notebooklm login` opens a browser (or imports cookies) so the script can authenticate via `NotebookLMClient.from_storage()`.

## Usage

```bash
# From a web / YouTube URL
python generate_video.py --url "https://example.com/article" --output video.mp4

# From a local file
python generate_video.py --file notes.pdf --format brief --style classic

# From pasted text
python generate_video.py --text "Summary of our product launch" --instructions "Keep it under 2 minutes"
```

### Options

| Flag | Description |
|------|-------------|
| `--url` / `--file` / `--text` | Source material (exactly one required) |
| `--title` | Notebook title (default: derived from source) |
| `--instructions` | Optional prompt for the video |
| `--format` | `explainer` (default), `brief`, `cinematic` |
| `--style` | `whiteboard` (default), `auto`, `classic`, `kawaii`, `anime`, `watercolor`, `retro-print`, `heritage`, `paper-craft`, `custom` |
| `--style-prompt` | Required with `--style custom` |
| `--language` | Output language code (default: `en`) |
| `--output` | MP4 path (default: `./output.mp4`) |
| `--timeout` | Wait budget in seconds (default: 1800; 3600 for cinematic) |

`--style` is not used for `--format cinematic`. Cinematic videos use Veo 3 and require a Google AI Ultra subscription.

## Auth troubleshooting

If the script reports a missing storage file or auth/cookie errors:

```bash
notebooklm login
notebooklm auth check --test
```

## Google Search trends

[`fetch_trends.py`](fetch_trends.py) pulls the current top Google Search trends (Google Trends RSS via [trendspyg](https://github.com/flack0x/trendspyg)). No API key required.

```bash
python fetch_trends.py --geo US
python fetch_trends.py --geo CA --output trends_canada.txt
python fetch_trends.py --geo GB --limit 20 --output trends.txt
```

Results are saved to `trends.txt` by default (top 20 by search volume). Uses Google Trends CSV export (Chrome required); falls back to RSS if CSV fails.

## YouTube trending videos

[`fetch_youtube_trends.py`](fetch_youtube_trends.py) fetches YouTube’s most popular videos via the official [YouTube Data API v3](https://developers.google.com/youtube/v3/docs/videos/list) (`chart=mostPopular`).

### API key setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **YouTube Data API v3**
3. Create an API key
4. Export it (see [`.env.example`](.env.example)):

```bash
export YOUTUBE_API_KEY='your-key'
```

### Usage

```bash
python fetch_youtube_trends.py
python fetch_youtube_trends.py --geo CA --output youtube_trends_canada.txt
python fetch_youtube_trends.py --limit 20 --api-key 'your-key'
```

Results are saved to `youtube_trends.txt` by default (title, channel, views, URL).
