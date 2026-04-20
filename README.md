# yt2apple

Convert YouTube playlists (or long mix videos) to Apple Music playlists — no Apple Developer account required.

## How it works

Apple Music's web player at `music.apple.com` ships a developer token inside its JavaScript bundle. yt2apple fetches that bundle, extracts the token via regex, and uses it against Apple's MusicKit API — the same API the web player uses. No $99/year Apple Developer account needed.

User authentication is a single `media-user-token` cookie from your browser session. Apple Music cookies last up to 180 days, so you only need to paste it once. Credentials are stored locally in `~/.config/yt2apple/config.json`.

## Prerequisites

- Python 3.11+
- An Apple Music subscription
- A browser logged in to [music.apple.com](https://music.apple.com)

## Installation

```bash
pip install .
```

Or install in editable mode during development:

```bash
pip install -e .
```

## Usage

**Step 1 — authenticate once:**

```bash
yt2apple setup
```

This prompts you to paste your `media-user-token` browser cookie and saves it locally.

**Step 2 — convert:**

```bash
yt2apple convert <url>
```

Examples:

```bash
# YouTube playlist
yt2apple convert "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxx"

# Single long mix video (tracks parsed from timestamp description)
yt2apple convert "https://www.youtube.com/watch?v=xxxxxxxxxxx"
```

The tool creates a new Apple Music playlist with the same name as the YouTube playlist (or video title), then searches Apple Music for each track and adds matches.

## Supported YouTube input formats

| Input | Track source |
|---|---|
| Playlist URL (`?list=...`) | Each video in the playlist |
| Single video with timestamps in description | Timestamp entries parsed as individual tracks |
| Single video without timestamps | Falls back to video title as a single track |

## Limitations

- Apple may change the JS bundle structure at any time, breaking developer token extraction. If this happens, open an issue.
- Videos without a timestamp description fall back to using the video title as the search query. Match quality varies.
- Apple Music search is fuzzy; tracks that are unavailable in your region or not on Apple Music will be skipped.
- The `media-user-token` cookie expires after roughly 180 days; re-run `yt2apple setup` to refresh it.

## Disclaimer

yt2apple uses Apple's unofficial MusicKit web API — the same endpoints the `music.apple.com` web player uses. This is not sanctioned by Apple and may break without notice. Use at your own risk.
