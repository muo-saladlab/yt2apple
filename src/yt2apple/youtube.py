import re
from dataclasses import dataclass

import yt_dlp


@dataclass
class Track:
    title: str
    artist: str | None = None
    raw: str = ""

    def search_query(self) -> str:
        if self.artist:
            return f"{self.artist} {self.title}"
        return self.title


# Suffixes to strip from titles (case-insensitive)
_SUFFIX_PATTERN = re.compile(
    r"[\s\-]*"
    r"(?:"
    r"\(Official MV\)"
    r"|\(Official Video\)"
    r"|\(MV\)"
    r"|\[MV\]"
    r"|\(Lyric Video\)"
    r"|\(Audio\)"
    r"|\(Official Audio\)"
    r"|\[Official\]"
    r"|\(Official\)"
    r"|M/V"
    r"|\(Lyrics\)"
    r"|\(4K\)"
    r"|\[4K\]"
    r")",
    re.IGNORECASE,
)

# Matches "Korean(English)" or "English(Korean)" artist duplicates
_ARTIST_DUPE_PATTERN = re.compile(
    r"^([가-힣]+)\(([A-Za-z]+)\)$|^([A-Za-z]+)\(([가-힣]+)\)$"
)

# Timestamp line: optional bullet/number, optional HH:MM:SS or MM:SS, then content
_TIMESTAMP_LINE = re.compile(
    r"^(?:[\-\*\•]?\s*\d+[\.\)]\s*|\d+:\d+(?::\d+)?\s+)(.*\S)"
)


def _strip_suffixes(text: str) -> str:
    return _SUFFIX_PATTERN.sub("", text).strip()


def _normalise_artist(artist: str) -> str:
    """Collapse 'Korean(English)' or 'English(Korean)' to the Korean form."""
    m = _ARTIST_DUPE_PATTERN.match(artist.strip())
    if m:
        # Keep Korean part
        korean = m.group(1) or m.group(4)
        return korean
    return artist.strip()


def _parse_title(raw: str) -> Track:
    """Parse a raw video title string into a Track."""
    cleaned = _strip_suffixes(raw)

    # Try "Artist - Title"
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        artist = _normalise_artist(parts[0].strip())
        title = parts[1].strip()
        return Track(title=title, artist=artist, raw=raw)

    # Try "Title (feat. Artist)"
    feat_match = re.search(r"^(.*?)\s+\(feat\.\s+(.+?)\)\s*$", cleaned, re.IGNORECASE)
    if feat_match:
        title = feat_match.group(1).strip()
        artist = feat_match.group(2).strip()
        return Track(title=title, artist=artist, raw=raw)

    # Fallback: raw title as-is
    return Track(title=cleaned, artist=None, raw=raw)


def _parse_description_tracks(description: str) -> list[Track]:
    """Extract tracks from a video description that contains timestamps or a numbered list."""
    tracks: list[Track] = []
    for line in description.splitlines():
        line = line.strip()
        if not line:
            continue

        # Try timestamp line first
        m = _TIMESTAMP_LINE.match(line)
        if m:
            content = m.group(1).strip()
            if content:
                tracks.append(_parse_title(content))

    return tracks


def extract_tracks(url: str) -> tuple[str, list[Track]]:
    """
    Given a YouTube URL (playlist or single video), return:
    - (playlist_name, list of Track)

    For playlists: each video title becomes a Track (parsed for artist/title)
    For single videos: description timestamps parsed for song list.
    If description has no timestamps, falls back to video title as single Track.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Playlist
    if info.get("_type") == "playlist" or "entries" in info:
        playlist_name: str = info.get("title") or "Unknown Playlist"
        tracks: list[Track] = []
        for entry in info.get("entries") or []:
            title = entry.get("title") or ""
            if title:
                tracks.append(_parse_title(title))
        return playlist_name, tracks

    # Single video
    video_title: str = info.get("title") or "Unknown"
    description: str = info.get("description") or ""
    tracks = _parse_description_tracks(description)
    if tracks:
        return video_title, tracks

    # Fallback: treat the video title itself as the single track
    return video_title, [_parse_title(video_title)]
